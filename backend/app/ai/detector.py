import threading
import logging
import os
from typing import List, Optional, Dict, Any
import numpy as np
import time
from pathlib import Path

from app.ai.tracker import Tracker

logger = logging.getLogger(__name__)


class Detector:
    """
    PERFECTED YOLO11 Person Detector with integrated tracking.
    - TensorRT optimization with caching.
    - Per-camera tracker instances for stable multi-camera operation.
    - Health monitoring (latency, failures) for Watchdog integration.
    - Configurable confidence, classes, and tracker params.
    """

    def __init__(
        self,
        model_path: str,
        device: str = "cpu",
        tracker_type: str = "botsort",   # "botsort" recommended for CCTV accuracy
        tracker_config: Optional[str] = None,
    ):
        self.model_path = model_path
        self.device = device
        self.tracker_type = tracker_type
        self.tracker_config = tracker_config

        self.lock = threading.Lock()
        self.model = None
        self.tracker = Tracker(tracker_type=tracker_type, tracker_config=tracker_config)

        # Health metrics
        self._health: Dict[str, Any] = {
            "last_inference": 0.0,
            "avg_latency": 0.0,
            "inference_count": 0,
            "error_count": 0,
        }

        self._load_model()

    def _load_model(self):
        """Load YOLO11 with TensorRT optimization (cached .engine)."""
        try:
            from ultralytics import YOLO

            self.model = YOLO(self.model_path)

            if self.device == "cuda":
                engine_path = self.model_path.replace('.pt', '.engine')
                engine_path = str(Path(engine_path).resolve())

                if not os.path.exists(engine_path):
                    logger.info(f"[Detector] Exporting to TensorRT engine (FP16 + dynamic) for speed...")
                    self.model.export(
                        format='engine',
                        half=True,
                        dynamic=True,
                        simplify=True,
                        workspace=8,          # GB for RTX 3050+
                    )
                    logger.info(f"[Detector] TensorRT export completed → {engine_path}")

                if os.path.exists(engine_path):
                    self.model = YOLO(engine_path)
                    logger.info(f"[Detector] ✅ Loaded optimized TensorRT engine: {engine_path}")
                else:
                    self.model.to(self.device)
            else:
                self.model.to(self.device)

            logger.info(f"[Detector] YOLO11 initialized on {self.device.upper()} | Tracker: {self.tracker_type.upper()}")
        except Exception as e:
            logger.error(f"[Detector] Model load failed: {e}")
            raise

    def detect(
        self,
        img_np: np.ndarray,
        camera_id: str,
        conf: float = 0.45,
        iou: float = 0.7,
        classes: List[int] = [0],   # person class
    ) -> List[Dict]:
        """
        Run detection + tracking on a frame.
        Returns list of enriched track dictionaries.
        """
        if self.model is None:
            return []

        start_time = time.perf_counter()

        try:
            with self.lock:
                results = self.model.track(
                    source=img_np,
                    conf=conf,
                    iou=iou,
                    classes=classes,
                    persist=True,               # Critical for maintaining IDs
                    verbose=False,
                    tracker=self.tracker_config or f"{self.tracker_type}.yaml",
                    imgsz=640,                  # Balance speed/accuracy; increase for small faces
                )

            # Pass to dedicated tracker for enrichment + state management
            tracks = self.tracker.update(results, camera_id, img_np)

            # Update health metrics
            latency = (time.perf_counter() - start_time) * 1000
            with self.lock:
                self._health["last_inference"] = time.time()
                self._health["inference_count"] += 1
                # Simple moving average latency
                self._health["avg_latency"] = (
                    (self._health["avg_latency"] * 0.95) + (latency * 0.05)
                )

            return tracks

        except Exception as e:
            logger.error(f"[Detector] Inference error on camera {camera_id}: {e}")
            with self.lock:
                self._health["error_count"] += 1
            return []

    def get_health(self) -> Dict:
        """Return health stats for Watchdog monitoring."""
        with self.lock:
            return {
                "device": self.device,
                "tracker_type": self.tracker_type,
                "avg_latency_ms": round(self._health["avg_latency"], 2),
                "inference_count": self._health["inference_count"],
                "error_rate": round(self._health["error_count"] / max(1, self._health["inference_count"]), 4),
                "last_inference_age": round(time.time() - self._health["last_inference"], 1),
            }

    def reset_tracker(self, camera_id: str):
        """Reset tracker state after stream reconnection."""
        self.tracker.reset_camera(camera_id)
