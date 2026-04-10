# Feature: face-detection-training, Property 11: ONNX output shape contract
"""
Property-based tests for ModelExporter._validate_output_shape.

**Validates: Requirements 4.2, 4.3**
"""

import sys
import os

# Ensure the backend app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "app"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import MagicMock

from app.ai.training.model_exporter import ModelExporter

# Strategy: generate 2-integer tuples that are NOT (1, 128)
wrong_shape_strategy = st.tuples(
    st.integers(min_value=1, max_value=512),
    st.integers(min_value=1, max_value=512),
).filter(lambda s: s != (1, 128))


def _make_mock_session(shape: tuple) -> MagicMock:
    """Build a mock onnxruntime.InferenceSession returning a tensor of *shape*."""
    mock_input = MagicMock()
    mock_input.name = "input"

    mock_session = MagicMock()
    mock_session.get_inputs.return_value = [mock_input]
    mock_session.run.return_value = [np.zeros(shape, dtype=np.float32)]

    return mock_session


@given(shape=wrong_shape_strategy)
@settings(max_examples=100)
def test_validate_output_shape_rejects_wrong_shapes(shape):
    """
    Property 11 (reject): For any output shape != (1, 128),
    _validate_output_shape must raise ValueError.

    **Validates: Requirements 4.2, 4.3**
    """
    mock_session = _make_mock_session(shape)
    exporter = ModelExporter()

    with pytest.raises(ValueError, match="ONNX output shape mismatch"):
        exporter._validate_output_shape(mock_session, (1, 3, 112, 112))


def test_validate_output_shape_accepts_correct_shape():
    """
    Property 11 (accept): When the output shape is exactly (1, 128),
    _validate_output_shape must succeed without raising.

    **Validates: Requirements 4.2, 4.3**
    """
    mock_session = _make_mock_session((1, 128))
    exporter = ModelExporter()

    result = exporter._validate_output_shape(mock_session, (1, 3, 112, 112))
    assert result == (1, 128)


# Feature: face-detection-training, Property 12: PyTorch–ONNX round-trip fidelity
"""
Property-based tests for ModelExporter._round_trip_verify.

**Validates: Requirements 7.1, 7.3**
"""

import torch


def _make_pt_mock(np_values: np.ndarray) -> MagicMock:
    """Return a mock PyTorch model that outputs a tensor built from *np_values*."""
    mock_model = MagicMock()
    mock_model.return_value = torch.from_numpy(np_values.copy())
    return mock_model


def _make_onnx_mock(np_values: np.ndarray) -> MagicMock:
    """Return a mock ONNX session that outputs *np_values*."""
    mock_input = MagicMock()
    mock_input.name = "input"

    mock_session = MagicMock()
    mock_session.get_inputs.return_value = [mock_input]
    mock_session.run.return_value = [np_values.copy()]
    return mock_session


# Strategy: generate a flat list of 128 float32 values for the [1, 128] output
_output_strategy = st.lists(
    st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    min_size=128,
    max_size=128,
)

# Strategy: perturbation strictly greater than 1e-4
_perturbation_strategy = st.floats(
    min_value=2e-4, max_value=1.0, allow_nan=False, allow_infinity=False
)


@given(output_values=_output_strategy)
@settings(max_examples=100)
def test_round_trip_verify_identical_outputs_pass(output_values):
    """
    Property 12 (scenario 1): When PT and ONNX outputs are identical,
    max_abs_diff == 0 and passed must be True.

    **Validates: Requirements 7.1, 7.3**
    """
    np_values = np.array(output_values, dtype=np.float32).reshape(1, 128)

    pt_mock = _make_pt_mock(np_values)
    onnx_mock = _make_onnx_mock(np_values)

    exporter = ModelExporter()
    report = exporter._round_trip_verify(pt_mock, onnx_mock, (1, 3, 112, 112), rtol=1e-4)

    assert report.passed is True
    assert report.max_abs_diff < 1e-4
    assert report.passed == (report.max_abs_diff < 1e-4)


@given(output_values=_output_strategy, perturbation=_perturbation_strategy)
@settings(max_examples=100)
def test_round_trip_verify_differing_outputs_fail(output_values, perturbation):
    """
    Property 12 (scenario 2): When ONNX output differs from PT output by more
    than 1e-4, passed must be False.

    **Validates: Requirements 7.1, 7.3**
    """
    pt_np = np.array(output_values, dtype=np.float32).reshape(1, 128)
    # Perturb the first element by an amount strictly > 1e-4
    onnx_np = pt_np.copy()
    onnx_np[0, 0] += perturbation

    pt_mock = _make_pt_mock(pt_np)
    onnx_mock = _make_onnx_mock(onnx_np)

    exporter = ModelExporter()
    report = exporter._round_trip_verify(pt_mock, onnx_mock, (1, 3, 112, 112), rtol=1e-4)

    assert report.passed is False
    assert report.max_abs_diff >= 1e-4
    assert report.passed == (report.max_abs_diff < 1e-4)
