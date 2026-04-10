"""
Face Trainer
============
Wraps the Ultralytics YOLO.train() API with progress callbacks,
cancellation support, and per-epoch metric logging.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class TrainConfig:
    data_yaml: str
    base_model: str = "yolo11n.pt"
    epochs: int = 50          # [1, 300]
    batch_size: int = 16
    learning_rate: float = 0.01
    imgsz: int = 640
    device: str = "cpu"
    output_dir: str = "models/face_detection_trained"

    def __post_init__(self) -> None:
        if not (1 <= self.epochs <= 300):
            raise ValueError(
                f"epochs must be in [1, 300], got {self.epochs}"
            )
        if self.batch_size < 1:
            raise ValueError(
                f"batch_size must be >= 1, got {self.batch_size}"
            )
        if self.learning_rate <= 0:
            raise ValueError(
                f"learning_rate must be > 0, got {self.learning_rate}"
            )


@dataclass
class TrainResult:
    best_pt: str
    last_pt: str
    final_map50: float
    log_path: str


class FaceTrainer:
    """Fine-tunes a YOLOv11-face model using the Ultralytics training API."""

    def __init__(self, cancel_event: threading.Event) -> None:
        self._cancel_event = cancel_event

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def train(
        self,
        config: TrainConfig,
        progress_cb: Callable[[int, dict], None],
    ) -> TrainResult:
        """
        Fine-tune the base model using *config* and return a TrainResult.

        Args:
            config:      Training hyperparameters and paths.
            progress_cb: Called after each epoch with (epoch_number, metrics).

        Returns:
            TrainResult with paths to best.pt / last.pt, final mAP@0.5,
            and the training log path.

        Raises:
            ValueError:    If config parameters are out of valid range.
            StopIteration: Propagated when training is cancelled via
                           cancel_event (raised inside the epoch callback).
        """
        from ultralytics import YOLO

        device = self._select_device()
        logger.info(
            "[FaceTrainer] Starting training on device=%s, epochs=%d, "
            "batch=%d, lr=%g, imgsz=%d",
            device, config.epochs, config.batch_size,
            config.learning_rate, config.imgsz,
        )

        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        log_path = output_dir / "training.log"

        # Set up a file handler for per-epoch metric logging
        file_handler = logging.FileHandler(str(log_path))
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(message)s")
        )
        train_logger = logging.getLogger("face_trainer.metrics")
        train_logger.addHandler(file_handler)
        train_logger.setLevel(logging.INFO)

        model = YOLO(config.base_model)

        # Mutable container so the nested callback can write back state
        _state: dict = {"last_map50": 0.0, "cancelled": False}

        def _on_epoch_end(trainer) -> None:  # noqa: ANN001
            """Per-epoch callback: log metrics, call progress_cb, check cancel."""
            epoch: int = trainer.epoch + 1  # Ultralytics is 0-indexed
            metrics: dict = {}

            # Extract available metrics from the trainer
            if hasattr(trainer, "metrics") and trainer.metrics:
                metrics = dict(trainer.metrics)
            elif hasattr(trainer, "loss_items") and trainer.loss_items is not None:
                metrics["loss"] = float(trainer.loss_items.mean())

            map50 = float(metrics.get("metrics/mAP50(B)", 0.0))
            if map50:
                _state["last_map50"] = map50

            # Log to file
            train_logger.info(
                "epoch=%d/%d  map50=%.4f  metrics=%s",
                epoch, config.epochs, map50, metrics,
            )

            # Notify caller
            try:
                progress_cb(epoch, metrics)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[FaceTrainer] progress_cb raised: %s", exc)

            # Check cancellation
            if self._cancel_event.is_set():
                logger.info(
                    "[FaceTrainer] Cancel event set at epoch %d — stopping.", epoch
                )
                _state["cancelled"] = True
                raise StopIteration("Training cancelled by cancel_event")

        model.add_callback("on_train_epoch_end", _on_epoch_end)

        results = None
        try:
            results = model.train(
                data=config.data_yaml,
                epochs=config.epochs,
                batch=config.batch_size,
                lr0=config.learning_rate,
                imgsz=config.imgsz,
                device=device,
                project=str(output_dir.parent),
                name=output_dir.name,
                exist_ok=True,
                verbose=False,
            )
        except StopIteration:
            # Cancellation — save whatever checkpoint Ultralytics has written
            logger.info("[FaceTrainer] Training stopped early (cancelled).")
        except Exception as exc:
            logger.error(
                "[FaceTrainer] Training failed with exception: %s", exc,
                exc_info=True,
            )
            raise
        finally:
            file_handler.close()
            train_logger.removeHandler(file_handler)

        # Resolve checkpoint paths from Ultralytics results or fall back to
        # the expected output directory layout.
        if results is not None and hasattr(results, "save_dir"):
            save_dir = Path(results.save_dir)
        else:
            save_dir = output_dir

        weights_dir = save_dir / "weights"
        best_pt = str(weights_dir / "best.pt")
        last_pt = str(weights_dir / "last.pt")

        # Retrieve final mAP@0.5 from results if available
        final_map50 = _state["last_map50"]
        if results is not None and hasattr(results, "results_dict"):
            final_map50 = float(
                results.results_dict.get("metrics/mAP50(B)", final_map50)
            )

        logger.info(
            "[FaceTrainer] Done. best=%s  last=%s  mAP50=%.4f",
            best_pt, last_pt, final_map50,
        )

        return TrainResult(
            best_pt=best_pt,
            last_pt=last_pt,
            final_map50=final_map50,
            log_path=str(log_path),
        )

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _select_device(self) -> str:
        """Return 'cuda' if a CUDA-capable GPU is available, else 'cpu'."""
        try:
            import torch

            if torch.cuda.is_available():
                logger.info("[FaceTrainer] CUDA available — using GPU.")
                return "cuda"
        except ImportError:
            pass
        logger.info("[FaceTrainer] No CUDA — falling back to CPU.")
        return "cpu"
