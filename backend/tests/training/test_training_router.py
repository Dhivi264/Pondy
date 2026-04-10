"""
Unit tests for the training router HTTP error cases.

Validates: Requirements 5.6
"""

from __future__ import annotations

import sys
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure the backend app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "app"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.routers.training_router import router
from app.ai.training.pipeline import ConflictError, TrainingJob

# ---------------------------------------------------------------------------
# Test app setup
# ---------------------------------------------------------------------------

app = FastAPI()
app.include_router(router, prefix="/api/training")
client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_JOB_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _make_mock_job(job_id: str = MOCK_JOB_ID) -> TrainingJob:
    job = TrainingJob(job_id=job_id, total_epochs=50)
    job.status = "training"
    job.current_epoch = 5
    job.metrics = {"loss": 0.42}
    job.started_at = datetime(2024, 1, 1, 12, 0, 0)
    job.ended_at = None
    job.error = None
    return job


VALID_START_PAYLOAD = {
    "source_dir": "/data/videos",
    "epochs": 10,
    "batch_size": 8,
    "learning_rate": 0.01,
    "frame_interval": 1.0,
}

# ---------------------------------------------------------------------------
# POST /start
# ---------------------------------------------------------------------------


def test_start_returns_409_when_job_already_running():
    """POST /start returns 409 when training_pipeline.start_job raises ConflictError."""
    with patch("app.routers.training_router.training_pipeline") as mock_pipeline:
        mock_pipeline.start_job.side_effect = ConflictError("already running")
        response = client.post("/api/training/start", json=VALID_START_PAYLOAD)

    assert response.status_code == 409
    assert "already" in response.json()["detail"].lower()


def test_start_returns_200_with_job_id_on_success():
    """POST /start returns 200 with job_id when start_job succeeds."""
    with patch("app.routers.training_router.training_pipeline") as mock_pipeline:
        mock_pipeline.start_job.return_value = MOCK_JOB_ID
        response = client.post("/api/training/start", json=VALID_START_PAYLOAD)

    assert response.status_code == 200
    assert response.json()["job_id"] == MOCK_JOB_ID


# ---------------------------------------------------------------------------
# GET /status/{job_id}
# ---------------------------------------------------------------------------


def test_get_status_returns_404_for_unknown_job_id():
    """GET /status/{job_id} returns 404 when training_pipeline.get_job returns None."""
    with patch("app.routers.training_router.training_pipeline") as mock_pipeline:
        mock_pipeline.get_job.return_value = None
        response = client.get(f"/api/training/status/{MOCK_JOB_ID}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_status_returns_200_with_job_data_on_success():
    """GET /status/{job_id} returns 200 with job data when job exists."""
    mock_job = _make_mock_job()
    with patch("app.routers.training_router.training_pipeline") as mock_pipeline:
        mock_pipeline.get_job.return_value = mock_job
        response = client.get(f"/api/training/status/{MOCK_JOB_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == MOCK_JOB_ID
    assert data["status"] == "training"
    assert data["current_epoch"] == 5
    assert data["total_epochs"] == 50


# ---------------------------------------------------------------------------
# POST /cancel/{job_id}
# ---------------------------------------------------------------------------


def test_cancel_returns_404_for_unknown_job_id():
    """POST /cancel/{job_id} returns 404 when training_pipeline.cancel_job returns False."""
    with patch("app.routers.training_router.training_pipeline") as mock_pipeline:
        mock_pipeline.cancel_job.return_value = False
        response = client.post(f"/api/training/cancel/{MOCK_JOB_ID}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
