"""
LMP-TX Background Worker
========================
Runs the AI video pipeline in the background.
Spawns threads for each camera and processes frames real-time.
"""

import threading
import logging
import pyodbc
import os
import yaml
from app.access_db import get_connection_string
from app.repositories.attendance_repository import AttendanceRepository
from app.lmp_tx.event_manager import EventManager
from app.lmp_tx.frame_processor import StreamProcessor, HardwareProfile
from app.lmp_tx.camera_config import CameraConfig, config_registry

logger = logging.getLogger(__name__)


class BackgroundWorker:
    def __init__(self):
        self.threads = []
        self.stop_event = threading.Event()

    def start_cameras(self):
        """Load cameras from YAML and start processing threads."""
        yaml_path = "cameras.yaml"
        if not os.path.exists(yaml_path):
            logger.error(f"[Worker] {yaml_path} not found. No cameras to start.")
            return

        try:
            with open(yaml_path, "r") as f:
                cam_data = yaml.safe_load(f)

            # Global DB connection for the repository (threads will use their own)
            # Actually, EventManager needs a repo, and repo needs a DB conn.
            # We'll create one per thread for safety.

            for cam_id, cfg in cam_data.items():
                t = threading.Thread(
                    target=self._run_camera, args=(cam_id, cfg), daemon=True
                )
                t.start()
                self.threads.append(t)
                logger.info(f"[Worker] Started thread for {cam_id}")

        except Exception as e:
            logger.error(f"[Worker] Failed to start cameras: {e}")

    def _run_camera(self, camera_id: str, cfg_dict: dict):
        """Individual camera processing loop."""
        # Create a private DB connection for this thread
        conn = pyodbc.connect(get_connection_string())
        repo = AttendanceRepository(conn)
        mgr = EventManager(repo)

        # Register config
        cfg = CameraConfig(
            camera_id=camera_id,
            url=cfg_dict.get("url", ""),
            conf_threshold=cfg_dict.get("conf_threshold", 0.5),
            frame_skip=cfg_dict.get("frame_skip", 5),
            classes=cfg_dict.get("classes", [0]),
            roi=cfg_dict.get("roi"),
            roi_polygon=cfg_dict.get("roi_polygon"),
            queue_size=cfg_dict.get("queue_size", 30),
            retries=cfg_dict.get("retries", -1),
            auto_reconnect=cfg_dict.get("auto_reconnect", True),
        )
        config_registry.set(cfg)

        proc = StreamProcessor.from_hardware_profile(
            profile=HardwareProfile.AUTO, event_mgr=mgr
        )

        logger.info(f"[Worker] {camera_id} loop entered.")
        try:
            # This is an infinite generator unless stream dies and no reconnect
            for _ in proc.process_stream_with_config(camera_id):
                if self.stop_event.is_set():
                    break
        except Exception as e:
            logger.error(f"[Worker] {camera_id} error: {e}")
        finally:
            conn.close()
            logger.info(f"[Worker] {camera_id} loop exited.")


_worker = BackgroundWorker()


def start_background_analysis():
    _worker.start_cameras()
