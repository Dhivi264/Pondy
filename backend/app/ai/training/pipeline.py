"""
Training Pipeline
=================
Orchestrates the full face detection training workflow:
  dataset collection → dataset preparation → model training → ONNX export

Exposes a thread-safe job registry and a module-level singleton.
"""

from __future__ import annotations

import logging
import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ConflictError(Exception):
    """Raised when a training job is already active."""


class DatasetError(Exception):
    """Raised when the dataset does not meet minimum requirements."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

_ACTIVE_STATUSES = frozenset(
    ["pending", "collecting", "preparing", "training", "exporting"]
)


@dataclass
class TrainingJobConfig:
    source_dir: str
    epochs: int = 50
    batch_size: int = 16
    learning_rate: float = 0.01
    frame_interval: float = 1.0
    device: str | None = None   # None = auto-detect
    skip_collection: bool = False


class TrainingJob:
    """Represents a single end-to-end training run."""

    def __init__(self, job_id: str, total_epochs: int) -> None:
        self.job_id: str = job_id
        self.status: Literal[
            "pending", "collecting", "preparing", "training",
            "exporting", "completed", "failed", "cancelled"
        ] = "pending"
        self.current_epoch: int = 0
        self.total_epochs: int = total_epochs
        self.metrics: dict = {}
        self.started_at: datetime = datetime.utcnow()
        self.ended_at: datetime | None = None
        self.error: str | None = None
        self.cancel_event: threading.Event = threading.Event()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class TrainingPipeline:
    """Manages training jobs and runs the pipeline in background threads."""

    def __init__(self) -> None:
        self._jobs: dict[str, TrainingJob] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def start_job(self, config: TrainingJobConfig) -> str:
        """
        Validate *config*, create a new TrainingJob, and launch it in a
        background thread.

        Returns:
            The new job's UUID string.

        Raises:
            ConflictError: if any job is currently in an active status.
        """
        with self._lock:
            for job in self._jobs.values():
                if job.status in _ACTIVE_STATUSES:
                    raise ConflictError(
                        "A training job is already in progress"
                    )

            job_id = str(uuid.uuid4())
            job = TrainingJob(job_id=job_id, total_epochs=config.epochs)
            self._jobs[job_id] = job

        thread = threading.Thread(
            target=self._run,
            args=(job, config),
            daemon=True,
            name=f"training-{job_id[:8]}",
        )
        thread.start()
        logger.info("[TrainingPipeline] Started job %s.", job_id)
        return job_id

    def get_job(self, job_id: str) -> TrainingJob | None:
        """Return the TrainingJob for *job_id*, or None if not found."""
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> list[TrainingJob]:
        """Return a snapshot list of all known jobs."""
        with self._lock:
            return list(self._jobs.values())

    def cancel_job(self, job_id: str) -> bool:
        """
        Signal the job to cancel after the current epoch.

        Returns:
            True if the job was active and the cancel signal was sent,
            False if the job does not exist or is not active.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status not in _ACTIVE_STATUSES:
                return False
            job.cancel_event.set()
            logger.info("[TrainingPipeline] Cancel requested for job %s.", job_id)
            return True

    # ------------------------------------------------------------------ #
    # Background worker                                                    #
    # ------------------------------------------------------------------ #

    def _run(self, job: TrainingJob, config: TrainingJobConfig) -> None:
        """
        Execute the full pipeline in a background thread.

        Status transitions:
            pending → collecting → preparing → training → exporting → completed
            (any active state) → failed   (on unhandled exception)
            (any active state) → cancelled (on StopIteration / cancel_event)
        """
        try:
            # ── 1. Collection ──────────────────────────────────────────
            if not config.skip_collection:
                job.status = "collecting"
                logger.info("[TrainingPipeline] [%s] Collecting dataset.", job.job_id)
                self._collect_dataset(job, config)
            else:
                logger.info(
                    "[TrainingPipeline] [%s] Skipping collection.", job.job_id
                )

            # ── 2. Preparation ─────────────────────────────────────────
            job.status = "preparing"
            logger.info("[TrainingPipeline] [%s] Preparing dataset.", job.job_id)
            data_yaml_path = self._prepare_dataset(job, config)

            # ── 3. Training ────────────────────────────────────────────
            job.status = "training"
            logger.info("[TrainingPipeline] [%s] Training model.", job.job_id)
            train_result = self._train_model(job, config, data_yaml_path)

            # ── 4. Export ──────────────────────────────────────────────
            job.status = "exporting"
            logger.info("[TrainingPipeline] [%s] Exporting model.", job.job_id)
            self._export_model(job, train_result)

            # ── 5. Done ────────────────────────────────────────────────
            job.status = "completed"
            job.ended_at = datetime.utcnow()
            logger.info("[TrainingPipeline] [%s] Completed.", job.job_id)

            # Best-effort gallery reload
            self._reload_gallery()

        except StopIteration:
            job.status = "cancelled"
            job.ended_at = datetime.utcnow()
            logger.info("[TrainingPipeline] [%s] Cancelled.", job.job_id)

        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.error = str(exc)
            job.ended_at = datetime.utcnow()
            logger.error(
                "[TrainingPipeline] [%s] Failed: %s", job.job_id, exc,
                exc_info=True,
            )

    # ------------------------------------------------------------------ #
    # Pipeline stages                                                      #
    # ------------------------------------------------------------------ #

    def _collect_dataset(
        self, job: TrainingJob, config: TrainingJobConfig
    ) -> None:
        """Run DatasetCollector.collect()."""
        from app.ai.training.dataset_collector import (
            CollectionConfig,
            DatasetCollector,
        )

        collector = DatasetCollector()
        collection_config = CollectionConfig(
            source_dir=config.source_dir,
            frame_interval=config.frame_interval,
        )
        summary = collector.collect(collection_config)
        logger.info(
            "[TrainingPipeline] [%s] Collection summary: %s",
            job.job_id, summary,
        )

    def _prepare_dataset(
        self, job: TrainingJob, config: TrainingJobConfig
    ) -> str:
        """
        Validate, deduplicate, split, and write data.yaml.

        Returns:
            Path to the generated data.yaml file.

        Raises:
            DatasetError: if fewer than 10 valid images are found.
        """
        import cv2
        import imagehash
        from PIL import Image

        images_dir = Path("data/faces/images")
        data_yaml = Path("data/faces/data.yaml")

        # ── Scan for valid images ──────────────────────────────────────
        candidates = sorted(
            p for p in images_dir.glob("*")
            if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        )

        valid: list[Path] = []
        for img_path in candidates:
            try:
                img = cv2.imread(str(img_path))
                if img is not None and img.size > 0:
                    valid.append(img_path)
                else:
                    logger.warning(
                        "[TrainingPipeline] Skipping unreadable image: %s",
                        img_path,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[TrainingPipeline] Skipping corrupt image %s: %s",
                    img_path, exc,
                )

        if len(valid) < 10:
            raise DatasetError(
                f"Dataset has only {len(valid)} valid image(s); "
                "at least 10 are required."
            )

        # ── Deduplicate via perceptual hash ────────────────────────────
        HASH_THRESHOLD = 8
        kept: list[Path] = []
        hashes: list = []

        for img_path in valid:
            try:
                phash = imagehash.phash(Image.open(img_path))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[TrainingPipeline] Cannot hash %s, keeping it: %s",
                    img_path, exc,
                )
                kept.append(img_path)
                continue

            is_dup = any(
                abs(phash - existing) < HASH_THRESHOLD for existing in hashes
            )
            if not is_dup:
                kept.append(img_path)
                hashes.append(phash)
            else:
                logger.debug(
                    "[TrainingPipeline] Duplicate removed: %s", img_path
                )

        logger.info(
            "[TrainingPipeline] [%s] After dedup: %d / %d images kept.",
            job.job_id, len(kept), len(valid),
        )

        # ── Train / val split ──────────────────────────────────────────
        n = len(kept)
        train_size = math.floor(n * 0.8)
        val_size = n - train_size

        train_imgs = kept[:train_size]
        val_imgs = kept[train_size:]

        # Create split subdirectories and symlink / copy images + labels
        train_dir = images_dir / "train"
        val_dir = images_dir / "val"
        train_dir.mkdir(parents=True, exist_ok=True)
        val_dir.mkdir(parents=True, exist_ok=True)

        self._populate_split(train_imgs, train_dir)
        self._populate_split(val_imgs, val_dir)

        logger.info(
            "[TrainingPipeline] [%s] Split: train=%d, val=%d.",
            job.job_id, train_size, val_size,
        )

        # ── Write data.yaml ────────────────────────────────────────────
        yaml_content = (
            "path: data/faces\n"
            "train: images/train\n"
            "val: images/val\n"
            "nc: 1\n"
            'names: ["face"]\n'
        )
        data_yaml.parent.mkdir(parents=True, exist_ok=True)
        data_yaml.write_text(yaml_content, encoding="utf-8")
        logger.info(
            "[TrainingPipeline] [%s] data.yaml written to %s.",
            job.job_id, data_yaml,
        )

        return str(data_yaml)

    def _populate_split(self, images: list[Path], dest_dir: Path) -> None:
        """
        Copy images (and their corresponding label files) into *dest_dir*.
        """
        import shutil

        labels_src = Path("data/faces/labels")
        labels_dst = dest_dir.parent.parent / "labels" / dest_dir.name
        labels_dst.mkdir(parents=True, exist_ok=True)

        for img_path in images:
            # Copy image
            shutil.copy2(str(img_path), str(dest_dir / img_path.name))
            # Copy label if it exists
            lbl_path = labels_src / (img_path.stem + ".txt")
            if lbl_path.exists():
                shutil.copy2(str(lbl_path), str(labels_dst / lbl_path.name))

    def _train_model(
        self,
        job: TrainingJob,
        config: TrainingJobConfig,
        data_yaml_path: str,
    ):
        """Run FaceTrainer.train() and return a TrainResult."""
        from app.ai.training.face_trainer import FaceTrainer, TrainConfig

        device = config.device or "cpu"

        train_config = TrainConfig(
            data_yaml=data_yaml_path,
            epochs=config.epochs,
            batch_size=config.batch_size,
            learning_rate=config.learning_rate,
            device=device,
        )

        def _progress_cb(epoch: int, metrics: dict) -> None:
            job.current_epoch = epoch
            job.metrics = metrics

        trainer = FaceTrainer(cancel_event=job.cancel_event)
        return trainer.train(train_config, progress_cb=_progress_cb)

    def _export_model(self, job: TrainingJob, train_result) -> None:
        """Run ModelExporter.export()."""
        from app.ai.training.model_exporter import ExportConfig, ModelExporter

        export_config = ExportConfig(
            checkpoint_path=train_result.best_pt,
        )
        exporter = ModelExporter()
        exporter.export(export_config)

    def _reload_gallery(self) -> None:
        """
        Best-effort: trigger FaceRecognizer gallery reload after export.
        Failures are logged but do not affect job status.
        """
        try:
            from app.ai.face_recognizer import FaceRecognizer
            from app.database import SessionLocal
            from app import crud

            db = SessionLocal()
            try:
                employees = crud.get_all_employees(db)
                emp_dicts = [
                    {"id": e.id, "face_image_path": e.face_image_path}
                    for e in employees
                ]
            finally:
                db.close()

            recognizer = FaceRecognizer()
            recognizer.load_gallery(emp_dicts)
            logger.info(
                "[TrainingPipeline] Gallery reloaded with %d employees.",
                len(emp_dicts),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[TrainingPipeline] Gallery reload skipped: %s", exc
            )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

training_pipeline = TrainingPipeline()
