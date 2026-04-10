"""
Clip Manager — saves snapshots and MP4 clips from AI detection events.
"""

import os
import logging
import numpy as np
import cv2
from datetime import datetime
from typing import List, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class ClipManager:
    """
    Handles event recording and archival.
    Saves JPEG snapshots and short MP4 clips to RECORDINGS_DIR.
    """

    def __init__(self):
        self.output_dir = settings.RECORDINGS_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def save_snapshot(
        self,
        frame_np: np.ndarray,
        employee_id: Optional[int],
        camera_id: int,
    ) -> str:
        """Save a JPEG snapshot of the detected person. Returns saved path."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            emp_tag = str(employee_id) if employee_id else "unknown"
            filename = f"snap_cam{camera_id}_emp{emp_tag}_{timestamp}.jpg"
            path = os.path.join(self.output_dir, filename)
            img_bgr = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
            cv2.imwrite(path, img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
            logger.debug(f"[ClipManager] Snapshot saved: {path}")
            return path
        except Exception as e:
            logger.error(f"[ClipManager] Snapshot error: {e}")
            return ""

    def save_clip(
        self,
        frames: List[np.ndarray],
        camera_id: int,
        employee_id: Optional[int] = None,
        fps: int = 10,
    ) -> str:
        """Encode a list of RGB numpy frames into an MP4 clip. Returns saved path."""
        if not frames:
            return ""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            emp_tag = str(employee_id) if employee_id else "unknown"
            filename = f"clip_cam{camera_id}_emp{emp_tag}_{timestamp}.mp4"
            path = os.path.join(self.output_dir, filename)

            h, w = frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(path, fourcc, fps, (w, h))

            for frame in frames:
                writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

            writer.release()
            logger.info(f"[ClipManager] Clip saved ({len(frames)} frames): {path}")
            return path
        except Exception as e:
            logger.error(f"[ClipManager] Clip error: {e}")
            return ""
