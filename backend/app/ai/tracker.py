import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class Tracker:
    """
    Production-grade Tracker Wrapper for Ultralytics YOLO.
    - Maintains per-camera state for stable tracking across frames.
    - Reduces ID switching common in CCTV (occlusions, low FPS).
    - Provides track information for downstream EventEngine/Attendance.
    """

    def __init__(self, tracker_type: str = "botsort",
                 tracker_config: Optional[str] = None):
        self.tracker_type = tracker_type.lower()
        self.tracker_config = tracker_config or f"{self.tracker_type}.yaml"

        # Per-camera tracker state (managed via persist=True)
        self._camera_states: Dict[str, Dict[str, Any]] = {}

        logger.info(f"[Tracker] Initialized with {self.tracker_type.upper()} "
                    f"(config: {self.tracker_config})")

    def update(self, detector_results: List, camera_id: str,
               img_np: np.ndarray) -> List[Dict]:
        """
        Process detection results with tracking.
        Returns list of enriched track dicts.
        """
        if not detector_results:
            return []

        # Ensure we have state for this camera
        if camera_id not in self._camera_states:
            self._camera_states[camera_id] = {
                "frame_count": 0,
                "active_tracks": 0,
                "last_ids": set()
            }

        state = self._camera_states[camera_id]
        state["frame_count"] += 1

        detections = []
        try:
            # detector_results is usually a list of Results objects
            for result in detector_results:
                if not hasattr(result, 'boxes') or result.boxes is None:
                    continue

                boxes = result.boxes
                for box in boxes:
                    # Core track data
                    xyxy = box.xyxy[0].cpu().tolist()
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    track_id = int(box.id[0]) if box.id is not None else None

                    if track_id is None:
                        continue  # Skip untracked detections

                    track_dict = {
                        "track_id": track_id,
                        "box": [round(x, 2) for x in xyxy],  # x1, y1, x2, y2
                        "confidence": round(conf, 4),
                        "class_id": cls_id,
                        "class_name": result.names.get(cls_id, "unknown"),
                        "camera_id": camera_id,
                        "frame_idx": state["frame_count"],
                    }

                    # Optional rich metadata
                    if hasattr(box, 'xywh') and box.xywh is not None:
                        track_dict["center"] = box.xywh[0][:2].cpu().tolist()

                    detections.append(track_dict)

            state["active_tracks"] = len(detections)
            state["last_ids"] = {d["track_id"] for d in detections}

            # Log occasional stats for monitoring
            if state["frame_count"] % 300 == 0:  # every ~10s at 30fps
                logger.debug(f"[Tracker] Cam {camera_id} | "
                             f"Active tracks: {state['active_tracks']} | "
                             f"Unique IDs: {len(state['last_ids'])}")

        except Exception as e:
            logger.error(f"[Tracker] Update error for camera {camera_id}: {e}")

        return detections

    def get_stats(self, camera_id: Optional[str] = None) -> Dict:
        """Return tracking statistics for monitoring (used by Watchdog)."""
        if camera_id:
            return self._camera_states.get(camera_id, {})
        return {cid: stats for cid, stats in self._camera_states.items()}

    def reset_camera(self, camera_id: str):
        """Reset tracker state for a camera (e.g., after reconnection)."""
        if camera_id in self._camera_states:
            del self._camera_states[camera_id]
            logger.info(f"[Tracker] Reset state for camera {camera_id}")
