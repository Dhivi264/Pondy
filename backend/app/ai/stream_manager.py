import av
import threading
import queue
import time
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class StreamManager:
    """
    Manages multiple RTSP camera streams using PyAV for high-performance decoding.
    Handles frame buffering, skipping, and health monitoring.
    """

    def __init__(self):
        self.active_streams: Dict[str, threading.Thread] = {}
        self._latest_frame: Dict[str, Optional[Tuple[datetime, object]]] = {}
        # --- Dual Pipeline Separation (STRICT) ---
        self._ai_queues: Dict[str, queue.Queue] = {}
        # -----------------------------------------
        self._running: Dict[str, bool] = {}
        self._health: Dict[str, str] = {}
        self._last_frame_time: Dict[str, float] = {}
        self._frame_counts: Dict[str, int] = {}
        self._video_writers: Dict[str, object] = {}
        self._video_start_time: Dict[str, float] = {}
        self._RECORDING_CHUNK_SECONDS = 300  # 5 minutes

    def add_camera(self, camera_id: str, url: str, queue_size: int = 5):
        """Start a background thread to ingest a camera stream."""
        if camera_id in self.active_streams:
            self.stop_camera(camera_id)

        self._latest_frame[camera_id] = None
        self._ai_queues[camera_id] = queue.Queue(maxsize=1)  # AI Pipeline
        self._running[camera_id] = True
        self._health[camera_id] = "connecting"
        self._frame_counts[camera_id] = 0

        thread = threading.Thread(
            target=self._ingest_loop,
            args=(camera_id, url),
            name=f"Stream-{camera_id}",
            daemon=True,
        )
        thread.start()
        self.active_streams[camera_id] = thread
        logger.info(f"[Stream] Added camera {camera_id}: {url}")

    def stop_camera(self, camera_id: str):
        """Stop a specific camera stream."""
        self._running[camera_id] = False
        if camera_id in self.active_streams:
            self.active_streams[camera_id].join(timeout=2.0)
            del self.active_streams[camera_id]
        if camera_id in self._latest_frame:
            del self._latest_frame[camera_id]
        if camera_id in self._video_writers:
            if self._video_writers[camera_id]:
                self._video_writers[camera_id].release()
            del self._video_writers[camera_id]
        if camera_id in self._video_start_time:
            del self._video_start_time[camera_id]
        logger.info(f"[Stream] Stopped camera {camera_id}")

    def get_frame(
        self, camera_id: str, timeout: float = 1.0
    ) -> Optional[Tuple[datetime, object]]:
        """Retrieve the latest frame for LIVE VIEW (fast route)."""
        return self._latest_frame.get(camera_id)

    def get_ai_frame(
        self, camera_id: str, timeout: float = 0.5
    ) -> Optional[Tuple[datetime, object]]:
        """Consume a frame for AI processing (background route)."""
        if camera_id not in self._ai_queues:
            return None
        try:
            return self._ai_queues[camera_id].get(timeout=timeout)
        except queue.Empty:
            return None

    def get_health(self, camera_id: str) -> str:
        """Return the health status of a camera."""
        return self._health.get(camera_id, "unknown")

    def _ingest_loop(self, camera_id: str, url: str):
        """Internal loop for frame ingestion."""
        # Handle local webcam (index 0, 1, 2, etc.)
        if url.isdigit():
            cam_index = int(url)
            logger.info(f"[Stream] Opening local webcam {cam_index}...")
            self._health[camera_id] = "connecting"
            import cv2
            cap = None
            try:
                cap = cv2.VideoCapture(cam_index)
                if not cap.isOpened():
                    self._health[camera_id] = "error: cannot open webcam"
                    logger.error(f"[Stream] Failed to open webcam {cam_index}")
                    time.sleep(5)
                    return
                    
                while self._running[camera_id]:
                    ret, frame = cap.read()
                    if not ret:
                        self._health[camera_id] = "error: cannot read frame"
                        logger.warning(f"[Stream] Webcam {cam_index} read error, retrying...")
                        time.sleep(1)
                        cap = cv2.VideoCapture(cam_index)
                        continue
                    
                    frame = cv2.resize(frame, (640, 480))
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert to RGB for display
                    self._push_frame(camera_id, frame)
                    self._health[camera_id] = "online"
                    time.sleep(0.03)  # ~30fps cap
                    
            except Exception as e:
                self._health[camera_id] = "error: webcam exception"
                logger.error(f"[Stream] Webcam error: {e}")
            finally:
                if cap:
                    cap.release()
            return

        consecutive_fails = 0
        MAX_FAILS = 5  # Stop spamming after 5 consecutive grab failures

        while self._running[camera_id]:
            # RTSP/Remote stream via PyAV
            container = None
            try:
                # Force TCP transport for stable multi-camera connections
                container = av.open(
                    url, 
                    timeout=5.0, 
                    options={'rtsp_transport': 'tcp', 'stimeout': '5000000'}
                )
                stream = container.streams.video[0]
                stream.thread_type = "AUTO"

                self._health[camera_id] = "online"
                logger.info(f"[Stream] Connected to remote {camera_id} via TCP")

                for frame in container.decode(video=0):
                    if not self._running[camera_id]:
                        break

                    img = frame.to_image()
                    self._push_frame(camera_id, img)
                    self._last_frame_time[camera_id] = time.time()

            except Exception as e:
                self._health[camera_id] = f"error: {str(e)}"
                logger.error(f"[Stream] {camera_id} remote error: {e}")
                time.sleep(5)
            finally:
                if container:
                    container.close()

    def _push_frame(self, camera_id: str, img):
        """Helper to push frame to dual buffers (Stream + AI) and save to disk."""
        # 0. Continuous Recording to disk in chunks
        import cv2
        import numpy as np
        import os
        from app.config import settings
        
        try:
            now_ts = time.time()
            start_ts = self._video_start_time.get(camera_id, 0)
            
            # Start new chunk if none exists or time limit (5 mins) exceeded
            if camera_id not in self._video_writers or self._video_writers.get(camera_id) is None or (now_ts - start_ts > self._RECORDING_CHUNK_SECONDS):
                if camera_id in self._video_writers and self._video_writers[camera_id]:
                    self._video_writers[camera_id].release()
                    
                os.makedirs(settings.RECORDINGS_DIR, exist_ok=True)
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"camera_{camera_id}_{timestamp_str}.avi"
                filepath = os.path.join(settings.RECORDINGS_DIR, filename)
                
                if hasattr(img, 'shape'):
                    h, w = img.shape[:2]
                else:
                    w, h = img.size
                
                fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                self._video_writers[camera_id] = cv2.VideoWriter(filepath, fourcc, 15.0, (w, h))
                self._video_start_time[camera_id] = now_ts
                logger.info(f"[Stream] Started continuous recording chunk: {filepath}")
                
            writer = self._video_writers[camera_id]
            if writer:
                frame_np = np.array(img)
                frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
                writer.write(frame_bgr)
        except Exception as e:
            logger.error(f"[Stream] Continuous recording error for camera {camera_id}: {e}")

        # 1. STREAM PIPELINE: Fast update for MJPEG proxy
        now = datetime.now()
        self._latest_frame[camera_id] = (now, img)

        # 2. AI PIPELINE: Non-blocking push for background processing
        if camera_id in self._ai_queues:
            q = self._ai_queues[camera_id]
            try:
                # If AI is slow and queue is full, drop the old frame
                if q.full():
                    q.get_nowait()
                q.put_nowait((now, img))
            except queue.Full:
                pass
            except queue.Empty:
                pass


stream_manager = StreamManager()
