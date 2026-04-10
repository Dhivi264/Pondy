"""
LMP-TX Face Recognition Service — YOLOv11-powered
===================================================
Replaces the old dlib / face_recognition / buffalo_l approach entirely.
Uses the shared app.ai.FaceRecognizer which depends only on:
  - ultralytics (YOLOv11)  ← already installed
  - onnxruntime             ← already installed
  - opencv-python           ← already installed
"""

import os
import logging
import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FaceMatch:
    employee_id: str
    confidence: float
    is_match: bool


class FaceRecognizer:
    """
    Singleton wrapper around app.ai.FaceRecognizer for the LMP-TX event pipeline.
    Gallery dir: data/faces (one JPEG per employee, filename = employee_id).
    """

    _instance: Optional["FaceRecognizer"] = None

    def __init__(self, gallery_dir: str = "data/faces"):
        self.gallery_dir = gallery_dir
        self.known_embeddings: List[np.ndarray] = []
        self.known_ids: List[str] = []
        self.is_ready = False

        # Use the shared YOLOv11-based engine
        from app.ai.face_recognizer import FaceRecognizer as _Engine

        self._engine = _Engine()
        self._load_gallery()

    @classmethod
    def get_instance(cls) -> "FaceRecognizer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_gallery(self):
        """Load all face images from gallery_dir and build the embedding list."""
        if not os.path.exists(self.gallery_dir):
            os.makedirs(self.gallery_dir, exist_ok=True)
            logger.warning(
                f"[LmpFaceRec] Gallery dir {self.gallery_dir} not found. Created it."
            )
            return

        import cv2

        for filename in os.listdir(self.gallery_dir):
            if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            employee_id = os.path.splitext(filename)[0]
            path = os.path.join(self.gallery_dir, filename)

            try:
                img = cv2.imread(path)
                if img is None:
                    continue
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                emb = self._engine.get_embedding(img_rgb)
                if emb is not None:
                    self.known_embeddings.append(emb)
                    self.known_ids.append(employee_id)
                    logger.info(f"[LmpFaceRec] Enrolled: {employee_id}")
                else:
                    logger.warning(f"[LmpFaceRec] No face found in {filename}")
            except Exception as e:
                logger.error(f"[LmpFaceRec] Failed to load {filename}: {e}")

        self.is_ready = len(self.known_embeddings) > 0
        logger.info(f"[LmpFaceRec] Ready with {len(self.known_ids)} enrolled faces.")

    # ─── Public API ────────────────────────────────────────────────────────────

    def identify(
        self,
        frame_np: np.ndarray,
        box: Optional[Tuple[int, int, int, int]] = None,
        threshold: float = 0.55,
    ) -> FaceMatch:
        """
        Identify a person in a frame or a pre-cropped region.
        box format: (y1, x1, y2, x2)  [InsightFace / LMP-TX convention]
        """
        if not self.is_ready:
            return FaceMatch("unknown", 0.0, False)

        try:
            # Crop if box is provided
            if box:
                y1, x1, y2, x2 = box
                h, w = frame_np.shape[:2]
                y1, x1 = max(0, y1), max(0, x1)
                y2, x2 = min(h, y2), min(w, x2)
                crop = frame_np[y1:y2, x1:x2]
            else:
                crop = frame_np

            emb = self._engine.get_embedding(crop)
            if emb is None:
                return FaceMatch("unknown", 0.0, False)

            # Cosine similarity against gallery
            best_score = -1.0
            best_idx = -1
            for i, known_emb in enumerate(self.known_embeddings):
                score = float(np.dot(emb, known_emb))
                if score > best_score:
                    best_score = score
                    best_idx = i

            if best_idx >= 0 and best_score >= threshold:
                return FaceMatch(self.known_ids[best_idx], best_score, True)

            return FaceMatch("unknown", max(0.0, best_score), False)

        except Exception as e:
            logger.error(f"[LmpFaceRec] Identification error: {e}")
            return FaceMatch("unknown", 0.0, False)

    def enroll_new_face(self, employee_id: str, image_np: np.ndarray) -> bool:
        """Dynamically enroll a new face and save to the gallery directory."""
        try:
            import cv2

            emb = self._engine.get_embedding(image_np)
            if emb is None:
                logger.warning(
                    f"[LmpFaceRec] No face detected for employee {employee_id}"
                )
                return False

            # Save to disk
            path = os.path.join(self.gallery_dir, f"{employee_id}.jpg")
            cv2.imwrite(path, cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR))

            # Add to in-memory gallery
            self.known_embeddings.append(emb)
            self.known_ids.append(str(employee_id))
            self.is_ready = True

            logger.info(f"[LmpFaceRec] Enrolled new face for {employee_id}")
            return True

        except Exception as e:
            logger.error(f"[LmpFaceRec] Enrollment failed for {employee_id}: {e}")
            return False
