"""
Training Router
===============
FastAPI endpoints for managing face detection training jobs.

Prefix: /api/training  (set in main.py)
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ai.training.pipeline import (
    ConflictError,
    TrainingJob,
    TrainingJobConfig,
    training_pipeline,
)

router = APIRouter(tags=["training"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class StartTrainingRequest(BaseModel):
    source_dir: str
    epochs: int = Field(default=50, ge=1, le=300)
    batch_size: int = Field(default=16, ge=1)
    learning_rate: float = Field(default=0.01, gt=0)
    frame_interval: float = Field(default=1.0, gt=0)


class TrainingJobResponse(BaseModel):
    job_id: str
    status: str
    current_epoch: int
    total_epochs: int
    metrics: dict
    started_at: datetime
    ended_at: datetime | None
    error: str | None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _job_to_response(job: TrainingJob) -> TrainingJobResponse:
    return TrainingJobResponse(
        job_id=job.job_id,
        status=job.status,
        current_epoch=job.current_epoch,
        total_epochs=job.total_epochs,
        metrics=job.metrics,
        started_at=job.started_at,
        ended_at=job.ended_at,
        error=job.error,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/start")
def start_training(request: StartTrainingRequest):
    """Start a new training job. Returns 409 if a job is already running."""
    config = TrainingJobConfig(
        source_dir=request.source_dir,
        epochs=request.epochs,
        batch_size=request.batch_size,
        learning_rate=request.learning_rate,
        frame_interval=request.frame_interval,
    )
    try:
        job_id = training_pipeline.start_job(config)
    except ConflictError:
        raise HTTPException(
            status_code=409,
            detail="A training job is already in progress",
        )
    return {"job_id": job_id}


@router.get("/status/{job_id}", response_model=TrainingJobResponse)
def get_training_status(job_id: str):
    """Get the status and metrics of a training job. Returns 404 if not found."""
    job = training_pipeline.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.post("/cancel/{job_id}")
def cancel_training(job_id: str):
    """Cancel a running training job. Returns 404 if not found or not active."""
    cancelled = training_pipeline.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": "cancellation requested"}


@router.get("/jobs", response_model=list[TrainingJobResponse])
def list_training_jobs():
    """List all training jobs."""
    return [_job_to_response(job) for job in training_pipeline.list_jobs()]
