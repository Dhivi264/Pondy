"""
Dataset Collector
=================
Scans CCTV footage directories, samples frames, detects faces using a
lightweight YOLO face model, and writes YOLO-format crops + labels to disk.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Supported video extensions (lower-case)
_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv"}


class CollectionError(Exception):
    """Raised when dataset collection cannot proceed."""


@dataclass
class CollectionConfig:
    source_dir: str
    output_dir: str = "data/faces"
    frame_interval: float = 1.0   # seconds between sampled frames
    conf_threshold: float = 0.40
    padding: int = 10             # pixels added around each detected bbox


@dataclass
class CollectionSummary:
    frames_sampled: int
    faces_detected: int
    images_saved: int
    skipped_files: list[str] = field(default_factory=list)


class DatasetCollector:
    """Collects labeled face crops from video files for YOLO training."""

    def __init__(self) -> None:
        self._yolo_model = None  # lazy-loaded on first use

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def collect(self, config: CollectionConfig) -> CollectionSummary:
        """
        Orchestrate scanning, sampling, detection, and saving.

        Raises:
            CollectionError: if source_dir is missing or contains no
                             supported video files.
        """
        source = Path(config.source_dir)
        if not source.exists():
            raise CollectionError(
                f"Source directory does not exist: {config.source_dir}"
            )

        videos = self._scan_videos(config.source_dir)
        if not videos:
            raise CollectionError(
                f"No supported video files (.mp4, .avi, .mkv) found in: "
                f"{config.source_dir}"
            )

        # Prepare output directories
        images_dir = Path(config.output_dir) / "images"
        labels_dir = Path(config.output_dir) / "labels"
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)

        frames_sampled = 0
        faces_detected = 0
        images_saved = 0
        skipped_files: list[str] = []
        face_idx = 0

        for video_path in videos:
            try:
                for frame in self._sample_frames(video_path, config.frame_interval):
                    frames_sampled += 1
                    bboxes = self._detect_faces(frame, config.conf_threshold)
                    faces_detected += len(bboxes)
                    for bbox in bboxes:
                        saved = self._save_crop_and_label(
                            frame, bbox, config.padding,
                            config.output_dir, face_idx
                        )
                        if saved:
                            images_saved += 1
                            face_idx += 1
            except _VideoOpenError:
                logger.warning(
                    "[DatasetCollector] Cannot open video, skipping: %s",
                    video_path,
                )
                skipped_files.append(str(video_path))

        return CollectionSummary(
            frames_sampled=frames_sampled,
            faces_detected=faces_detected,
            images_saved=images_saved,
            skipped_files=skipped_files,
        )

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _scan_videos(self, source_dir: str) -> list[Path]:
        """Recursively find .mp4, .avi, .mkv files (case-insensitive)."""
        root = Path(source_dir)
        found: list[Path] = []
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in _VIDEO_EXTENSIONS:
                found.append(path)
        return sorted(found)

    def _sample_frames(
        self, video_path: Path, interval: float
    ) -> Iterator[np.ndarray]:
        """
        Yield frames sampled at *interval* seconds from *video_path*.

        Raises:
            _VideoOpenError: if OpenCV cannot open the file.
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            cap.release()
            raise _VideoOpenError(str(video_path))

        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            frame_step = max(1, int(round(fps * interval)))
            frame_idx = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % frame_step == 0:
                    yield frame
                frame_idx += 1
        finally:
            cap.release()

    def _detect_faces(
        self, frame: np.ndarray, conf: float
    ) -> list[tuple[int, int, int, int]]:
        """
        Run a lightweight YOLO face model on *frame*.

        Returns a list of (x1, y1, x2, y2) integer bounding boxes whose
        confidence is >= *conf*.
        """
        model = self._get_yolo_model()
        results = model.predict(frame, conf=conf, verbose=False)
        boxes: list[tuple[int, int, int, int]] = []
        for r in results:
            for box in r.boxes:
                if float(box.conf[0]) >= conf:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    boxes.append((x1, y1, x2, y2))
        return boxes

    def _save_crop_and_label(
        self,
        frame: np.ndarray,
        bbox: tuple[int, int, int, int],
        padding: int,
        output_dir: str,
        idx: int,
    ) -> bool:
        """
        Crop the face region (with padding clamped to image bounds), save as
        JPEG, and write a YOLO-format .txt label for the *original* bbox.

        Returns True on success, False on any error.
        """
        try:
            h, w = frame.shape[:2]
            x1, y1, x2, y2 = bbox

            # Clamp padded crop to image bounds
            cx1 = max(0, x1 - padding)
            cy1 = max(0, y1 - padding)
            cx2 = min(w, x2 + padding)
            cy2 = min(h, y2 + padding)

            crop = frame[cy1:cy2, cx1:cx2]
            if crop.size == 0:
                return False

            stem = f"face_{idx:06d}"
            images_dir = Path(output_dir) / "images"
            labels_dir = Path(output_dir) / "labels"

            img_path = images_dir / f"{stem}.jpg"
            lbl_path = labels_dir / f"{stem}.txt"

            cv2.imwrite(str(img_path), crop)

            # YOLO label: class cx_norm cy_norm w_norm h_norm
            # Coordinates are relative to the *original* frame dimensions.
            cx_norm = ((x1 + x2) / 2.0) / w
            cy_norm = ((y1 + y2) / 2.0) / h
            w_norm = (x2 - x1) / w
            h_norm = (y2 - y1) / h

            lbl_path.write_text(
                f"0 {cx_norm:.6f} {cy_norm:.6f} {w_norm:.6f} {h_norm:.6f}\n"
            )
            return True

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[DatasetCollector] Failed to save crop/label idx=%d: %s",
                idx, exc,
            )
            return False

    # ------------------------------------------------------------------ #
    # Internal utilities                                                   #
    # ------------------------------------------------------------------ #

    def _get_yolo_model(self):
        """Lazy-load the YOLO face model (singleton per collector instance)."""
        if self._yolo_model is None:
            from ultralytics import YOLO

            candidates = [
                "models/yolo_face/yolov11n-face.pt",
                "models/yolo_face/yolo11n-face.pt",
                "yolov11n-face.pt",
                "yolo11n.pt",
            ]
            model_path = next(
                (p for p in candidates if os.path.exists(p)), candidates[-1]
            )
            self._yolo_model = YOLO(model_path)
            logger.info(
                "[DatasetCollector] Loaded YOLO face model: %s", model_path
            )
        return self._yolo_model


class _VideoOpenError(Exception):
    """Internal sentinel raised when cv2.VideoCapture cannot open a file."""
