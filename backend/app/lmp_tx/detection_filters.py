"""
Detection Filters
==================
Post-processes raw YOLO output through three sequential filters:

  1. Confidence Filter  — drops results below conf_threshold
  2. Class Filter       — keeps only the requested class IDs
  3. ROI Filter         — keeps only detections whose centre falls
                          inside the region of interest box/polygon

Each filter is a pure function: takes a list of detection dicts,
returns a (possibly shorter) list.  They compose cleanly:

    results = class_filter(conf_filter(raw, 0.5), [0, 2])
    results = roi_filter(results, roi=[100, 100, 500, 500])

Detection dict schema (what YOLO returns, normalised here):
    {
        "class_id":   int,
        "class_name": str,
        "confidence": float,   # 0.0 – 1.0
        "bbox":       [x1, y1, x2, y2],   # pixel coords
        "centre":     (cx, cy),
    }
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Normaliser — converts raw ultralytics Result into plain dicts
# ─────────────────────────────────────────────────────────────────


def normalise_detections(raw_results: Any) -> list[dict]:
    """
    Convert ultralytics Results (or stub [] output) into uniform dicts.
    Gracefully handles missing attributes so tests never crash.
    """
    detections: list[dict] = []

    if not raw_results:
        return detections

    for result in raw_results:
        try:
            boxes = result.boxes
        except AttributeError:
            continue

        if boxes is None:
            continue

        for box in boxes:
            try:
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = (
                    result.names.get(cls_id, f"class_{cls_id}")
                    if hasattr(result, "names")
                    else f"class_{cls_id}"
                )

                detections.append(
                    {
                        "class_id": cls_id,
                        "class_name": cls_name,
                        "confidence": round(conf, 4),
                        "bbox": [x1, y1, x2, y2],
                        "centre": ((x1 + x2) / 2, (y1 + y2) / 2),
                    }
                )
            except (IndexError, TypeError, AttributeError):
                continue

    return detections


# ─────────────────────────────────────────────────────────────────
# Filter 1 — Confidence threshold
# ─────────────────────────────────────────────────────────────────


def conf_filter(
    detections: list[dict],
    threshold: float = 0.5,
) -> list[dict]:
    """
    Drop detections whose confidence is below `threshold`.

    Setting threshold=0.5 means "only tell me if the model is at least
    50% certain". Values of 0.4–0.6 are typical for surveillance.
    Lower values catch more things but generate more false positives
    ("a bush blowing in the wind flagged as a person").
    """
    kept = [d for d in detections if d["confidence"] >= threshold]
    dropped = len(detections) - len(kept)
    if dropped:
        logger.debug(
            f"[conf_filter] threshold={threshold}: "
            f"kept {len(kept)}/{len(detections)} detections "
            f"(dropped {dropped} ghost detections)"
        )
    return kept


# ─────────────────────────────────────────────────────────────────
# Filter 2 — Class filter
# ─────────────────────────────────────────────────────────────────


def class_filter(
    detections: list[dict],
    classes: list[int] | None = None,
) -> list[dict]:
    """
    Keep only detections whose class_id is in `classes`.
    If classes is None or empty, return all detections unchanged.

    Common COCO IDs:
        0  person      2  car        3  motorcycle
        1  bicycle     5  bus        7  truck
    """
    if not classes:
        return detections

    class_set = set(classes)
    kept = [d for d in detections if d["class_id"] in class_set]
    dropped = len(detections) - len(kept)
    if dropped:
        logger.debug(
            f"[class_filter] classes={classes}: "
            f"kept {len(kept)}/{len(detections)} "
            f"(dropped {dropped} irrelevant classes)"
        )
    return kept


# ─────────────────────────────────────────────────────────────────
# Filter 3 — ROI filter (bbox and polygon)
# ─────────────────────────────────────────────────────────────────


def _point_in_rect(cx: float, cy: float, roi: list[int]) -> bool:
    x1, y1, x2, y2 = roi
    return x1 <= cx <= x2 and y1 <= cy <= y2


def _point_in_polygon(cx: float, cy: float, polygon: list[list[int]]) -> bool:
    """
    Ray-casting algorithm for point-in-polygon test.
    polygon: list of [x, y] vertex pairs, e.g. [[0,0],[100,0],[50,100]]
    """
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > cy) != (yj > cy)) and (
            cx < (xj - xi) * (cy - yi) / (yj - yi + 1e-9) + xi
        ):
            inside = not inside
        j = i
    return inside


def roi_filter(
    detections: list[dict],
    roi: list[int] | None = None,
    roi_polygon: list[list[int]] | None = None,
) -> list[dict]:
    """
    Keep only detections whose centre point falls inside the ROI.

    roi         : [x1, y1, x2, y2] bounding box (pixel coords)
    roi_polygon : [[x,y], [x,y], ...] arbitrary polygon vertices

    If both are None, all detections pass through unchanged.
    If both are set, roi_polygon takes precedence.

    Example:
        roi = [100, 100, 500, 500]
        # Only cares about a 400×400 pixel driveway region, ignores
        # the busy street visible in the rest of the camera frame.
    """
    if roi_polygon is None and roi is None:
        return detections

    kept: list[dict] = []
    for d in detections:
        cx, cy = d["centre"]
        if roi_polygon is not None:
            inside = _point_in_polygon(cx, cy, roi_polygon)
        else:
            inside = _point_in_rect(cx, cy, roi)  # type: ignore[arg-type]

        if inside:
            kept.append(d)

    dropped = len(detections) - len(kept)
    if dropped:
        logger.debug(
            f"[roi_filter] roi={roi or 'polygon'}: "
            f"kept {len(kept)}/{len(detections)} "
            f"({dropped} outside region of interest)"
        )
    return kept


# ─────────────────────────────────────────────────────────────────
# Composite pipeline — applies all filters in one call
# ─────────────────────────────────────────────────────────────────


def apply_all_filters(
    raw_results: Any,
    conf_threshold: float = 0.5,
    classes: list[int] | None = None,
    roi: list[int] | None = None,
    roi_polygon: list[list[int]] | None = None,
) -> list[dict]:
    """
    Normalise raw YOLO output then apply all three filters in order:
        normalise → conf_filter → class_filter → roi_filter

    Returns clean, filtered detection dicts ready for the LMP-TX
    fusion pipeline.
    """
    detections = normalise_detections(raw_results)
    detections = conf_filter(detections, conf_threshold)
    detections = class_filter(detections, classes)
    detections = roi_filter(detections, roi, roi_polygon)
    return detections
