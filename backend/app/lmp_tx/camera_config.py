"""
Camera Config — Central Parameter Store
========================================
Holds every per-camera tuning knob in one place and provides
a YAML loader that matches the config file format shown in the docs.

Supported parameters
--------------------
conf_threshold : float  [0.0–1.0]
    Minimum detection certainty to accept a result.
    Detections below this are silently dropped ("ghost" suppression).
    Typical range: 0.4 – 0.6.

roi : list[int] | None  → [x1, y1, x2, y2]
    Pixel-coordinate bounding box.  Only detections whose centre falls
    inside this rectangle are forwarded.  None = full frame.
    For polygon ROI, supply roi_polygon instead (list of [x, y] pairs).

queue_size : int
    Maximum number of frames held in the FrameBuffer at any time.
    When the buffer is full, the OLDEST frame is discarded so the
    consumer always gets the freshest frames (lag prevention).

classes : list[int] | None
    YOLO class IDs to keep.  All others are discarded.
    Common IDs (COCO):
        0  person        1  bicycle       2  car
        3  motorcycle    5  bus           7  truck
    None = keep every class.

retries : int
    How many times to attempt reconnection before giving up.
    Each retry waits an exponentially increasing delay
    (base 2 s, max 60 s).  Set to -1 for infinite retries.

auto_reconnect : bool
    If True, the stream processor will loop through reconnect attempts
    up to `retries` times on a stream drop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# COCO class ID → human-readable label (subset)
COCO_CLASSES: dict[int, str] = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    4: "airplane",
    5: "bus",
    6: "train",
    7: "truck",
    8: "boat",
    14: "bird",
    15: "cat",
    16: "dog",
    58: "potted plant",
    60: "dining table",
    63: "laptop",
    67: "cell phone",
}


# ─────────────────────────────────────────────────────────────────
# Core config dataclass
# ─────────────────────────────────────────────────────────────────


@dataclass
class CameraConfig:
    """All tuning parameters for a single camera stream."""

    camera_id: str
    url: str
    model: str = "yolov8n.pt"

    # 1. Confidence threshold
    conf_threshold: float = 0.5
    # 2. Region of Interest  [x1, y1, x2, y2] or None
    roi: Optional[list[int]] = None
    # 2b. Polygon ROI: list of [x, y] vertex pairs
    roi_polygon: Optional[list[list[int]]] = None
    # 3. Frame buffer / queue size
    queue_size: int = 30
    # 4. Class filter — COCO IDs, or None for all classes
    classes: Optional[list[int]] = None
    # 5. Reconnect
    retries: int = 5
    auto_reconnect: bool = True

    # Frame skip (from previous layer)
    frame_skip: int = 1

    # ── Derived helpers ────────────────────────────────────────────

    @property
    def class_names(self) -> list[str]:
        """Human-readable names for the configured class IDs."""
        if self.classes is None:
            return ["all"]
        return [COCO_CLASSES.get(c, f"class_{c}") for c in self.classes]

    def validate(self) -> list[str]:
        """Return a list of validation warnings (empty = all good)."""
        warnings: list[str] = []

        if not (0.0 <= self.conf_threshold <= 1.0):
            warnings.append(
                f"conf_threshold {self.conf_threshold} is outside [0, 1]. "
                "Clamping to 0.5."
            )
            self.conf_threshold = 0.5

        if self.roi is not None:
            if len(self.roi) != 4:
                warnings.append("roi must have exactly 4 elements [x1, y1, x2, y2].")
            elif self.roi[0] >= self.roi[2] or self.roi[1] >= self.roi[3]:
                warnings.append(
                    f"roi {self.roi} is invalid: x1 must < x2 and y1 must < y2."
                )

        if self.queue_size < 1:
            warnings.append("queue_size must be ≥ 1. Resetting to 30.")
            self.queue_size = 30

        if self.retries < -1:
            warnings.append("retries must be ≥ -1 (-1 = infinite). Resetting to 5.")
            self.retries = 5

        return warnings

    def summary(self) -> dict:
        return {
            "camera_id": self.camera_id,
            "model": self.model,
            "conf_threshold": self.conf_threshold,
            "roi": self.roi,
            "roi_polygon": self.roi_polygon,
            "queue_size": self.queue_size,
            "classes": self.classes,
            "class_names": self.class_names,
            "frame_skip": self.frame_skip,
            "retries": self.retries,
            "auto_reconnect": self.auto_reconnect,
        }


# ─────────────────────────────────────────────────────────────────
# Config Registry (in-memory store)
# ─────────────────────────────────────────────────────────────────


class CameraConfigRegistry:
    """
    Central store for all camera configs.
    Configs can be loaded from a YAML file or set individually via the API.
    """

    _configs: dict[str, CameraConfig] = {}

    def set(self, cfg: CameraConfig) -> list[str]:
        """Register / update a config. Returns any validation warnings."""
        warnings = cfg.validate()
        self._configs[cfg.camera_id] = cfg
        logger.info(f"[CamConfig] Registered {cfg.camera_id}: {cfg.summary()}")
        return warnings

    def get(self, camera_id: str) -> Optional[CameraConfig]:
        return self._configs.get(camera_id)

    def get_or_default(self, camera_id: str, url: str = "") -> CameraConfig:
        """Return existing config or a safe default."""
        return self._configs.get(camera_id, CameraConfig(camera_id=camera_id, url=url))

    def all(self) -> list[CameraConfig]:
        return list(self._configs.values())

    def delete(self, camera_id: str) -> bool:
        if camera_id in self._configs:
            del self._configs[camera_id]
            return True
        return False

    # ── YAML loader ───────────────────────────────────────────────

    def load_yaml(self, path: str | Path) -> dict[str, list[str]]:
        """
        Load a YAML config file and register all cameras.
        Returns a dict of {camera_id: [warnings]}.

        Expected format (matches the project documentation):

            camera_1:
              url: "rtsp://admin:pass@192.168.1.50:554/stream"
              model: "yolov8n.pt"
              conf_threshold: 0.5
              frame_skip: 5
              classes: [0, 2]
              roi: [100, 100, 500, 500]
              auto_reconnect: true
              queue_size: 30
              retries: 5
        """
        try:
            import yaml  # type: ignore
        except ImportError:
            raise ImportError(
                "PyYAML is required for YAML config loading. "
                "Install with: pip install pyyaml"
            )

        with open(path) as f:
            raw: dict = yaml.safe_load(f) or {}

        results: dict[str, list[str]] = {}
        for cam_id, params in raw.items():
            if not isinstance(params, dict):
                logger.warning(f"[CamConfig] Skipping {cam_id}: not a dict block.")
                continue
            cfg = CameraConfig(
                camera_id=cam_id,
                url=params.get("url", ""),
                model=params.get("model", "yolov8n.pt"),
                conf_threshold=float(params.get("conf_threshold", 0.5)),
                roi=params.get("roi"),
                roi_polygon=params.get("roi_polygon"),
                queue_size=int(params.get("queue_size", 30)),
                classes=params.get("classes"),
                retries=int(params.get("retries", 5)),
                auto_reconnect=bool(params.get("auto_reconnect", True)),
                frame_skip=int(params.get("frame_skip", 1)),
            )
            warnings = self.set(cfg)
            results[cam_id] = warnings

        logger.info(f"[CamConfig] Loaded {len(results)} cameras from {path}")
        return results

    def dump_yaml(self) -> str:
        """Serialise the full registry back to a YAML string."""
        try:
            import yaml  # type: ignore
        except ImportError:
            raise ImportError("PyYAML required. pip install pyyaml")

        data = {}
        for cam_id, cfg in self._configs.items():
            data[cam_id] = {
                "url": cfg.url,
                "model": cfg.model,
                "conf_threshold": cfg.conf_threshold,
                "frame_skip": cfg.frame_skip,
                "classes": cfg.classes,
                "roi": cfg.roi,
                "roi_polygon": cfg.roi_polygon,
                "queue_size": cfg.queue_size,
                "retries": cfg.retries,
                "auto_reconnect": cfg.auto_reconnect,
            }
        return yaml.dump(data, default_flow_style=False, sort_keys=False)


# Module-level singleton
config_registry = CameraConfigRegistry()
