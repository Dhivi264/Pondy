"""
LMP-TX Clip Recorder
====================
Handles the saving of short video clips (MP4) to disk when triggered by
AI detection events.
"""

import os
import cv2
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class ClipRecorder:
    """
    Helps record event-driven video clips from camera streams.
    """

    def __init__(self, output_dir: str = "data/recordings"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

    def record_clip(self, camera_id: str, frames: list, fps: int = 15) -> Optional[str]:
        """
        Record a list of frames as an MP4 file.
        Returns the path to the saved file.
        """
        if not frames:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{camera_id}_{timestamp}.mp4"
        filepath = os.path.join(self.output_dir, filename)

        try:
            h, w = frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore
            out = cv2.VideoWriter(filepath, fourcc, fps, (w, h))

            for frame in frames:
                out.write(frame)

            out.release()
            logger.info(f"[ClipRec] Saved event clip: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"[ClipRec] Failed to save clip: {e}")
            return None
