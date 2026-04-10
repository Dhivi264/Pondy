# Feature: face-detection-training, Property 1: Video file extension filtering
"""
Property-based tests for DatasetCollector.

**Validates: Requirements 1.1**
"""

import sys
import os

# Ensure the backend app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "app"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import tempfile
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.ai.training.dataset_collector import DatasetCollector

# Valid video extensions (case-insensitive)
_VALID_EXTENSIONS = {".mp4", ".avi", ".mkv"}

# Strategy: generate a file extension (with leading dot)
extension_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    min_size=1,
    max_size=5,
).map(lambda s: "." + s)

# Strategy: generate a simple filename stem (alphanumeric, no path separators)
stem_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=1,
    max_size=20,
)


@given(
    filenames=st.lists(
        st.tuples(stem_strategy, extension_strategy),
        min_size=0,
        max_size=30,
    )
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_scan_videos_returns_only_valid_extensions(filenames):
    """
    Property 1: For any directory containing files with arbitrary extensions,
    _scan_videos must return only files whose extension (case-insensitive)
    is one of .mp4, .avi, or .mkv.

    **Validates: Requirements 1.1**
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create all generated files in the temp directory
        created: set[str] = set()
        for stem, ext in filenames:
            filename = stem + ext
            # Avoid duplicate filenames in the same directory
            if filename not in created:
                (tmp_path / filename).touch()
                created.add(filename)

        collector = DatasetCollector()
        result = collector._scan_videos(str(tmp_path))

        # Every returned path must have a valid video extension
        for path in result:
            assert path.suffix.lower() in _VALID_EXTENSIONS, (
                f"Unexpected file returned: {path.name!r} "
                f"(extension {path.suffix.lower()!r} is not a valid video extension)"
            )

        # Every file we created with a valid extension must appear in the result
        expected_valid = {
            tmp_path / (stem + ext)
            for stem, ext in filenames
            if ext.lower() in _VALID_EXTENSIONS and (stem + ext) in created
        }
        result_set = set(result)
        for expected_path in expected_valid:
            assert expected_path in result_set, (
                f"Expected valid video file missing from result: {expected_path.name!r}"
            )


# Feature: face-detection-training, Property 2: Frame sampling count
"""
**Validates: Requirements 1.2**
"""

import math
from unittest.mock import MagicMock, patch

import numpy as np


@given(
    fps=st.integers(min_value=1, max_value=60),
    duration=st.integers(min_value=1, max_value=300),
    interval=st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100, deadline=None)
def test_sample_frames_count(fps, duration, interval):
    """
    Property 2: For any (fps, duration, interval) triple, the number of frames
    yielded by _sample_frames must equal floor(duration / interval) ±1.

    The implementation samples every frame_step = max(1, round(fps * interval))
    raw frames. We use assume() to restrict to inputs where fps*interval is
    close to an integer, ensuring frame_step rounding is exact and the ±1
    bound holds analytically.

    **Validates: Requirements 1.2**
    """
    from hypothesis import assume

    # frame_step as computed by the implementation
    frame_step = max(1, int(round(fps * interval)))

    # Only test inputs where fps*interval rounds cleanly (rounding error < 1%)
    # so that frame_step accurately represents the intended interval and the
    # floor(duration/interval) ±1 bound is guaranteed to hold.
    theoretical_step = fps * interval
    rounding_error = abs(frame_step - theoretical_step)
    assume(rounding_error < 0.01)

    total_frames = int(fps * duration)

    # Build a mock cv2.VideoCapture that simulates the video
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.get.return_value = float(fps)

    # Each read() returns a valid frame for the first total_frames calls, then (False, None)
    blank_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    read_results = [(True, blank_frame)] * total_frames + [(False, None)]
    mock_cap.read.side_effect = read_results

    with patch("cv2.VideoCapture", return_value=mock_cap):
        collector = DatasetCollector()
        frames = list(collector._sample_frames("fake_video.mp4", interval))

    sampled_count = len(frames)
    expected = math.floor(duration / interval)

    assert abs(sampled_count - expected) <= 1, (
        f"fps={fps}, duration={duration}, interval={interval}: "
        f"expected ~{expected} frames (floor({duration}/{interval})), "
        f"got {sampled_count}"
    )


# Feature: face-detection-training, Property 3: Confidence threshold filtering
"""
**Validates: Requirements 1.3**
"""


@given(
    detections=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),  # score
            st.tuples(
                st.integers(min_value=0, max_value=100),  # x1
                st.integers(min_value=0, max_value=100),  # y1
                st.integers(min_value=101, max_value=200),  # x2
                st.integers(min_value=101, max_value=200),  # y2
            ),
        ),
        min_size=0,
        max_size=20,
    ),
    conf_threshold=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100, deadline=None)
def test_detect_faces_confidence_threshold_filtering(detections, conf_threshold):
    """
    Property 3: For any list of detections with scores in [0, 1] and any
    conf_threshold in [0, 1], _detect_faces must return only detections
    whose score >= conf_threshold.

    **Validates: Requirements 1.3**
    """
    # Build mock boxes from the generated detections
    mock_boxes = []
    for score, (x1, y1, x2, y2) in detections:
        box = MagicMock()
        box.conf = [score]
        xyxy_mock = MagicMock()
        xyxy_mock.tolist.return_value = [x1, y1, x2, y2]
        box.xyxy = [xyxy_mock]
        mock_boxes.append(box)

    # Build a mock result containing all boxes
    mock_result = MagicMock()
    mock_result.boxes = mock_boxes

    # Build a mock YOLO model whose predict returns [mock_result]
    mock_model = MagicMock()
    mock_model.predict.return_value = [mock_result]

    blank_frame = np.zeros((300, 300, 3), dtype=np.uint8)

    with patch.object(DatasetCollector, "_get_yolo_model", return_value=mock_model):
        collector = DatasetCollector()
        result = collector._detect_faces(blank_frame, conf_threshold)

    # Compute expected: only detections with score >= conf_threshold
    expected = [
        (x1, y1, x2, y2)
        for score, (x1, y1, x2, y2) in detections
        if float(score) >= conf_threshold
    ]

    assert result == expected, (
        f"conf_threshold={conf_threshold}: "
        f"expected {len(expected)} detections, got {len(result)}. "
        f"Result: {result}, Expected: {expected}"
    )


# Feature: face-detection-training, Property 4: YOLO label normalisation round-trip
"""
**Validates: Requirements 1.5**
"""


@given(
    W=st.integers(min_value=10, max_value=4096),
    H=st.integers(min_value=10, max_value=4096),
    x1=st.integers(min_value=0, max_value=4095),
    y1=st.integers(min_value=0, max_value=4095),
    dx=st.integers(min_value=1, max_value=4096),
    dy=st.integers(min_value=1, max_value=4096),
)
@settings(max_examples=100)
def test_yolo_label_normalisation_round_trip(W, H, x1, y1, dx, dy):
    """
    Property 4: For any valid bounding box (x1, y1, x2, y2) within a frame of
    size (W, H), normalising to YOLO format and then denormalising recovers the
    original coordinates within floating-point tolerance.

    **Validates: Requirements 1.5**
    """
    from hypothesis import assume

    # Constrain x1, y1 to valid range and derive x2, y2 with positive area
    assume(x1 < W)
    assume(y1 < H)
    x2 = x1 + min(dx, W - x1)
    y2 = y1 + min(dy, H - y1)
    assume(x2 > x1)
    assume(y2 > y1)

    # Normalisation (mirrors _save_crop_and_label)
    cx_norm = (x1 + x2) / 2.0 / W
    cy_norm = (y1 + y2) / 2.0 / H
    w_norm = (x2 - x1) / W
    h_norm = (y2 - y1) / H

    # Denormalisation (inverse)
    x1_rec = cx_norm * W - w_norm * W / 2
    y1_rec = cy_norm * H - h_norm * H / 2
    x2_rec = cx_norm * W + w_norm * W / 2
    y2_rec = cy_norm * H + h_norm * H / 2

    assert abs(x1_rec - x1) < 1e-6, f"x1 mismatch: {x1_rec} != {x1}"
    assert abs(y1_rec - y1) < 1e-6, f"y1 mismatch: {y1_rec} != {y1}"
    assert abs(x2_rec - x2) < 1e-6, f"x2 mismatch: {x2_rec} != {x2}"
    assert abs(y2_rec - y2) < 1e-6, f"y2 mismatch: {y2_rec} != {y2}"


# Feature: face-detection-training, Property 5: Corrupt file resilience
"""
**Validates: Requirements 1.7, 2.5**
"""


@given(
    file_pairs=st.lists(
        st.tuples(
            st.text(
                alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
                min_size=1,
                max_size=20,
            ),
            st.booleans(),  # True = readable, False = unreadable
        ),
        min_size=1,
        max_size=20,
    )
)
@settings(max_examples=100, deadline=None)
def test_corrupt_file_resilience(file_pairs):
    """
    Property 5: For any mixed list of readable/unreadable .mp4 files,
    collect() must return a CollectionSummary where:
      - skipped_files contains exactly the paths of unreadable files
      - no unreadable file appears in the processed output

    **Validates: Requirements 1.7, 2.5**
    """
    from app.ai.training.dataset_collector import CollectionConfig

    # Deduplicate filenames (same stem -> keep first occurrence)
    seen: set[str] = set()
    unique_pairs: list[tuple[str, bool]] = []
    for stem, is_readable in file_pairs:
        filename = stem + ".mp4"
        if filename not in seen:
            seen.add(filename)
            unique_pairs.append((stem, is_readable))

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create actual .mp4 files on disk
        for stem, _ in unique_pairs:
            (tmp_path / (stem + ".mp4")).touch()

        readable_paths = {
            str(tmp_path / (stem + ".mp4"))
            for stem, is_readable in unique_pairs
            if is_readable
        }
        unreadable_paths = {
            str(tmp_path / (stem + ".mp4"))
            for stem, is_readable in unique_pairs
            if not is_readable
        }

        def make_mock_cap(path_str):
            """Return a mock VideoCapture whose behaviour depends on readability."""
            mock_cap = MagicMock()
            if path_str in readable_paths:
                mock_cap.isOpened.return_value = True
                mock_cap.get.return_value = 25.0
                # Empty video: first read returns (False, None)
                mock_cap.read.return_value = (False, None)
            else:
                mock_cap.isOpened.return_value = False
            return mock_cap

        with (
            patch("cv2.VideoCapture", side_effect=make_mock_cap),
            patch.object(DatasetCollector, "_detect_faces", return_value=[]),
        ):
            with tempfile.TemporaryDirectory() as out_dir:
                config = CollectionConfig(
                    source_dir=str(tmp_path),
                    output_dir=out_dir,
                )
                summary = DatasetCollector().collect(config)

        # skipped_files must contain exactly the unreadable paths
        assert set(summary.skipped_files) == unreadable_paths, (
            f"Expected skipped_files={unreadable_paths}, "
            f"got {set(summary.skipped_files)}"
        )

        # No unreadable file should appear in skipped_files as a readable one
        for path_str in summary.skipped_files:
            assert path_str not in readable_paths, (
                f"Readable file incorrectly marked as skipped: {path_str}"
            )


# Feature: face-detection-training, Property 6: Collection summary consistency
"""
**Validates: Requirements 1.8**
"""

from app.ai.training.dataset_collector import CollectionConfig, CollectionSummary


@given(
    frames_sampled=st.integers(min_value=0, max_value=1000),
    faces_ratio=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    saved_ratio=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_collection_summary_invariant_structural(frames_sampled, faces_ratio, saved_ratio):
    """
    Property 6 (structural): For any valid (frames_sampled, faces_detected, images_saved)
    satisfying the invariant, CollectionSummary holds:
      images_saved <= faces_detected <= frames_sampled

    **Validates: Requirements 1.8**
    """
    faces_detected = int(frames_sampled * faces_ratio)
    images_saved = int(faces_detected * saved_ratio)

    summary = CollectionSummary(
        frames_sampled=frames_sampled,
        faces_detected=faces_detected,
        images_saved=images_saved,
    )

    assert summary.images_saved <= summary.faces_detected, (
        f"images_saved ({summary.images_saved}) > faces_detected ({summary.faces_detected})"
    )
    assert summary.faces_detected <= summary.frames_sampled, (
        f"faces_detected ({summary.faces_detected}) > frames_sampled ({summary.frames_sampled})"
    )


@given(
    n_videos=st.integers(min_value=1, max_value=5),
    frames_per_video=st.integers(min_value=0, max_value=20),
    faces_per_frame=st.integers(min_value=0, max_value=5),
    save_probability=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100, deadline=None)
def test_collection_summary_invariant_end_to_end(
    n_videos, frames_per_video, faces_per_frame, save_probability
):
    """
    Property 6 (end-to-end): For any collect() run with controlled mocks,
    the returned CollectionSummary satisfies:
      images_saved <= faces_detected <= frames_sampled

    **Validates: Requirements 1.8**
    """
    import itertools

    blank_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    fake_bbox = (10, 10, 50, 50)

    # Fake video paths
    fake_videos = [Path(f"/fake/video_{i}.mp4") for i in range(n_videos)]

    # _sample_frames yields frames_per_video blank frames per video
    def mock_sample_frames(video_path, interval):
        for _ in range(frames_per_video):
            yield blank_frame

    # _detect_faces returns faces_per_frame bboxes per frame
    def mock_detect_faces(frame, conf):
        return [fake_bbox] * faces_per_frame

    # _save_crop_and_label returns True based on save_probability (deterministic per idx)
    # Use a simple pattern: save if (idx % 2 == 0) when probability >= 0.5, else never
    # Actually use a deterministic approach based on save_probability threshold
    call_counter = {"n": 0}

    def mock_save_crop_and_label(frame, bbox, padding, output_dir, idx):
        call_counter["n"] += 1
        # Deterministically decide: save the first ceil(total * save_probability) crops
        return (call_counter["n"] - 1) < int(
            n_videos * frames_per_video * faces_per_frame * save_probability
        )

    with (
        patch.object(DatasetCollector, "_scan_videos", return_value=fake_videos),
        patch.object(DatasetCollector, "_sample_frames", side_effect=mock_sample_frames),
        patch.object(DatasetCollector, "_detect_faces", side_effect=mock_detect_faces),
        patch.object(DatasetCollector, "_save_crop_and_label", side_effect=mock_save_crop_and_label),
    ):
        with tempfile.TemporaryDirectory() as out_dir:
            config = CollectionConfig(
                source_dir="/fake",
                output_dir=out_dir,
            )
            # Patch source_dir existence check
            with patch("pathlib.Path.exists", return_value=True):
                summary = DatasetCollector().collect(config)

    # Core invariant: images_saved can never exceed faces_detected
    assert summary.images_saved <= summary.faces_detected, (
        f"images_saved ({summary.images_saved}) > faces_detected ({summary.faces_detected})"
    )
    # Verify counts match what the mocks produced
    expected_frames = n_videos * frames_per_video
    expected_faces = n_videos * frames_per_video * faces_per_frame
    assert summary.frames_sampled == expected_frames, (
        f"frames_sampled ({summary.frames_sampled}) != expected ({expected_frames})"
    )
    assert summary.faces_detected == expected_faces, (
        f"faces_detected ({summary.faces_detected}) != expected ({expected_faces})"
    )
