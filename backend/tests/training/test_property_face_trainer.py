# Feature: face-detection-training, Property 10: Hyperparameter bounds validation
"""
Property-based tests for TrainConfig hyperparameter validation.

**Validates: Requirements 3.2, 3.8**
"""

import sys
import os

# Ensure the backend app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "app"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.ai.training.face_trainer import TrainConfig


@given(epochs=st.one_of(st.integers(max_value=0), st.integers(min_value=301)))
@settings(max_examples=100)
def test_invalid_epochs_raises_value_error(epochs):
    """
    Property 10 (invalid epochs): For any epochs outside [1, 300],
    TrainConfig must raise ValueError.

    **Validates: Requirements 3.2, 3.8**
    """
    with pytest.raises(ValueError):
        TrainConfig(data_yaml="data.yaml", epochs=epochs)


@given(batch_size=st.integers(max_value=0))
@settings(max_examples=100)
def test_invalid_batch_size_raises_value_error(batch_size):
    """
    Property 10 (invalid batch_size): For any batch_size < 1,
    TrainConfig must raise ValueError.

    **Validates: Requirements 3.2, 3.8**
    """
    with pytest.raises(ValueError):
        TrainConfig(data_yaml="data.yaml", batch_size=batch_size)


@given(
    lr=st.one_of(
        st.just(0.0),
        st.floats(max_value=0.0, allow_nan=False, allow_infinity=False),
    )
)
@settings(max_examples=100)
def test_invalid_learning_rate_raises_value_error(lr):
    """
    Property 10 (invalid learning_rate): For any learning_rate <= 0,
    TrainConfig must raise ValueError.

    **Validates: Requirements 3.2, 3.8**
    """
    with pytest.raises(ValueError):
        TrainConfig(data_yaml="data.yaml", learning_rate=lr)


@given(
    epochs=st.integers(min_value=1, max_value=300),
    batch_size=st.integers(min_value=1, max_value=256),
    lr=st.floats(min_value=1e-6, max_value=1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_valid_hyperparameters_no_exception(epochs, batch_size, lr):
    """
    Property 10 (valid values): For any valid (epochs, batch_size, lr),
    TrainConfig must instantiate without raising an exception.

    **Validates: Requirements 3.2, 3.8**
    """
    config = TrainConfig(
        data_yaml="data.yaml",
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=lr,
    )
    assert config.epochs == epochs
    assert config.batch_size == batch_size
    assert config.learning_rate == lr
