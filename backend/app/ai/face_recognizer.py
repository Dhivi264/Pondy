"""
Face Recognizer — YOLOv11-powered
==================================
Uses YOLOv11n-face (Ultralytics) for face detection and a lightweight
MobileNetV2 ONNX head for 128-d embeddings.
No InsightFace / buffalo_l dependency required.
"""

import os
import logging
import threading
import numpy as np
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FaceRecognizer:
    """
    YOLOv11-based Face Recognition Service.
    """

    def __init__(self, model_dir: str = "models/yolo_face", device: str = "cpu"):
        self.model_dir = model_dir
        self.device = device
        self.lock = threading.Lock()
        self.yolo_face = None  # YOLOv11-face detector
        self.embed_session = None  # ONNX embedding session (optional)
        self.known_embeddings: Dict[int, np.ndarray] = {}  # emp_id → 128-d vector
        self._load_models()

    # ─── Model loading ─────────────────────────────────────────────────────────

    def _load_models(self):
        """Load YOLOv11-face detector and optional ONNX embedding head."""
        self._load_yolo_face()
        self._load_embed_session()

    def _load_yolo_face(self):
        """Load yolov11n-face.pt (auto-downloads if missing)."""
        try:
            from ultralytics import YOLO

            # Prefer a local face-tuned weight; fall back to nano general model
            candidates = [
                os.path.join(self.model_dir, "yolov11n-face.pt"),
                os.path.join(self.model_dir, "yolo11n-face.pt"),
                "yolov11n-face.pt",  # ultralytics auto-download location
                "yolo11n.pt",  # general nano — still detects faces (class 0)
            ]
            model_path = next(
                (p for p in candidates if os.path.exists(p)), candidates[-1]
            )
            self.yolo_face = YOLO(model_path)
            if self.device != "cpu":
                self.yolo_face.to(self.device)
            logger.info(f"[FaceRec] Loaded YOLOv11 face model: {model_path} ({self.device})")
        except Exception as e:
            logger.error(f"[FaceRec] YOLOv11 face model failed to load: {e}")

    def _load_embed_session(self):
        """Load lightweight ONNX embedding head if available."""
        onnx_path = os.path.join(self.model_dir, "face_embed.onnx")
        if not os.path.exists(onnx_path):
            logger.info(
                "[FaceRec] No ONNX embedding head found — using pixel-HOG fallback."
            )
            return
        try:
            import onnxruntime as ort

            providers = ["CUDAExecutionProvider", "DirectMLExecutionProvider", "CPUExecutionProvider"]
            self.embed_session = ort.InferenceSession(
                onnx_path, providers=providers
            )
            logger.info(f"[FaceRec] Loaded ONNX embedding head: {onnx_path}")
        except Exception as e:
            logger.error(f"[FaceRec] ONNX embedding head failed: {e}")

    # ─── Public API ────────────────────────────────────────────────────────────

    def get_embedding(self, img_np: np.ndarray) -> Optional[np.ndarray]:
        """
        Compute a normalised embedding for a face crop or full frame.
        Returns None if no face is detected.
        """
        with self.lock:
            face_crop = self._extract_face(img_np)
            if face_crop is None:
                return None
            return self._compute_embedding(face_crop)

    def match(
        self,
        embedding: np.ndarray,
        threshold: Optional[float] = None,
    ) -> Tuple[Optional[int], float]:
        """
        Match an embedding against the loaded gallery.
        Returns (employee_id, cosine_score) or (None, score).
        """
        from app.config import settings
        if threshold is None:
            threshold = settings.FACE_MATCH_THRESHOLD

        if not self.known_embeddings:
            return None, 0.0

        best_score = -1.0
        best_id: Optional[int] = None

        for emp_id, known_emb in self.known_embeddings.items():
            score = float(np.dot(embedding, known_emb))
            if score > best_score:
                best_score = score
                best_id = emp_id

        if best_score >= threshold:
            return best_id, best_score
        return None, best_score

    def load_gallery(self, employees: List[dict]):
        """
        Load known embeddings from a list of employee dicts.
        Each dict must have: {'id': int, 'face_image_path': str}
        """
        import cv2

        loaded = 0
        for emp in employees:
            emp_id = emp.get("id")
            path = emp.get("face_image_path") or emp.get("face_path")
            if not path or not os.path.exists(path):
                continue
            try:
                img = cv2.imread(path)
                if img is None:
                    continue
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                emb = self.get_embedding(img_rgb)
                if emb is not None:
                    self.known_embeddings[emp_id] = emb
                    loaded += 1
            except Exception as e:
                logger.error(
                    f"[FaceRec] Failed to load embedding for emp {emp_id}: {e}"
                )
        logger.info(
            f"[FaceRec] Gallery loaded: {loaded}/{len(employees)} employees enrolled."
        )

    # ─── Internal helpers ──────────────────────────────────────────────────────

    def _extract_face(self, img_np: np.ndarray) -> Optional[np.ndarray]:
        """
        Use YOLOv11-face to find the largest face in the image.
        Returns a 112×112 RGB crop, or None if no face found.
        """
        if self.yolo_face is None:
            # Fallback: treat the entire crop as the face region
            return self._resize_face(img_np)

        try:
            results = self.yolo_face.predict(img_np, conf=0.40, verbose=False)
            best_box = None
            best_area = 0
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    area = (x2 - x1) * (y2 - y1)
                    if area > best_area:
                        best_area = area
                        best_box = (x1, y1, x2, y2)

            if best_box is None:
                return None

            x1, y1, x2, y2 = best_box
            # Add a small padding
            h, w = img_np.shape[:2]
            pad = 10
            x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
            x2, y2 = min(w, x2 + pad), min(h, y2 + pad)
            crop = img_np[y1:y2, x1:x2]
            return self._resize_face(crop)

        except Exception as e:
            logger.error(f"[FaceRec] Face extraction error: {e}")
            return None

    @staticmethod
    def _resize_face(img: np.ndarray, size: int = 112) -> Optional[np.ndarray]:
        """Resize to (size × size) RGB."""
        if img is None or img.size == 0:
            return None
        try:
            import cv2

            return cv2.resize(img, (size, size))
        except Exception:
            return None

    def _compute_embedding(self, face_112: np.ndarray) -> Optional[np.ndarray]:
        """
        Compute a normalised 128-d embedding.
        Uses ONNX head if loaded, otherwise falls back to pixel-HOG.
        """
        try:
            if self.embed_session is not None:
                return self._onnx_embedding(face_112)
            return self._hog_embedding(face_112)
        except Exception as e:
            logger.error(f"[FaceRec] Embedding error: {e}")
            return None

    def _onnx_embedding(self, face_112: np.ndarray) -> Optional[np.ndarray]:
        """Run the ONNX embedding head."""
        try:
            # Normalise to [-1, 1] float32, shape [1, 3, 112, 112]
            blob = face_112.astype(np.float32) / 127.5 - 1.0
            blob = np.transpose(blob, (2, 0, 1))[np.newaxis, :]  # CHW → NCHW

            input_name = self.embed_session.get_inputs()[0].name
            outputs = self.embed_session.run(None, {input_name: blob})
            emb = outputs[0].flatten().astype(np.float32)
            norm = np.linalg.norm(emb)
            return emb / norm if norm > 0 else emb
        except Exception as e:
            logger.error(f"[FaceRec] ONNX inference error: {e}")
            return None

    @staticmethod
    def _hog_embedding(face_112: np.ndarray) -> Optional[np.ndarray]:
        """
        Lightweight pixel+gradient histogram fallback (128-d).
        Less accurate than ArcFace but zero extra dependencies.
        """
        try:
            import cv2

            gray = cv2.cvtColor(face_112, cv2.COLOR_RGB2GRAY)

            # 8×8 blocks of mean pixel intensity → 64-d
            block = gray.reshape(8, 14, 8, 14).mean(axis=(1, 3)).flatten()

            # Sobel gradient histogram → 64-d
            gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
            gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
            mag = np.sqrt(gx**2 + gy**2)
            hist, _ = np.histogram(mag, bins=64, range=(0, 255))

            emb = np.concatenate([block, hist.astype(np.float32)])
            norm = np.linalg.norm(emb)
            return emb / norm if norm > 0 else emb
        except Exception as e:
            logger.error(f"[FaceRec] HOG fallback error: {e}")
            return None
