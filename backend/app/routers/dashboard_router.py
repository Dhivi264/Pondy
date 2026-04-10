from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth import get_current_user
from app.services.dashboard_service import DashboardService
from app.schemas import DashboardSummary
from app.models.user import User

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    service = DashboardService(db)
    return service.get_summary()


@router.get("/anomalies")
async def get_anomalies(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    from app.models.archive import ArchiveRecord
    anomalies = db.query(ArchiveRecord).filter(ArchiveRecord.event_type != "manual").order_by(ArchiveRecord.created_at.desc()).limit(20).all()
    # Convert to JSON serializable list
    return [{
        "id": a.id,
        "event_type": a.event_type,
        "title": a.title,
        "camera_id": a.camera_id,
        "employee_id": a.employee_id,
        "created_at": a.created_at,
        "severity": "high" if "anomaly" in a.event_type else "low"
    } for a in anomalies]


@router.get("/fusion-events")
async def get_fusion_events(
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.tracking import PersonSighting
    from app.models.employee import Employee
    
    sightings = db.query(PersonSighting).order_by(PersonSighting.last_seen.desc()).limit(limit).all()
    results = []
    for s in sightings:
        emp_name = "Unknown"
        if s.employee_id:
            emp = db.query(Employee).filter(Employee.id == s.employee_id).first()
            if emp: emp_name = emp.name
            
        results.append({
            "id": s.id,
            "employee_id": s.employee_id,
            "employee_name": emp_name,
            "camera_id": s.camera_id,
            "duration": s.duration_seconds,
            "timestamp": s.last_seen,
            "confidence": s.confidence_score
        })
    return results


@router.get("/hardware/profile")
async def get_hardware_profile(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return {
        "device": "CPU",
        "model": "yolo11n",
        "framework": "ultralytics/onnx",
        "skip_frames": 2,
    }


@router.get("/diagnostics/buffers")
async def get_diagnostics_buffers(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return {"active_streams": 1, "buffer_usage": 0}


@router.get("/profiles")
async def get_risk_profiles(
    window_days: int = 30,
    risk_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return []


@router.post("/al/start-session")
async def start_al_session(
    strategy: str = "uncertainty_sampling",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"status": "started", "strategy": strategy}


@router.get("/archive")
async def get_archive(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # Placeholder for archive records
    return []


@router.get("/al/pending-samples")
async def get_al_pending(
    limit: int = 15,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Placeholder for active learning
    return []


@router.post("/system/stop-ai")
async def stop_ai_engine(current_user: User = Depends(get_current_user)):
    """Manually stop all AI camera processing threads."""
    from app.workers.stream_worker import stream_worker

    stream_worker.stop()
    return {"status": "success", "message": "AI Engine stopped manually"}


@router.post("/system/start-ai")
async def start_ai_engine(current_user: User = Depends(get_current_user)):
    """Manually start/restart the AI camera processing engine."""
    from app.workers.stream_worker import stream_worker
    import threading

    if stream_worker._running:
        return {"status": "ignored", "message": "AI Engine is already running"}

    # Start in a background thread to avoid blocking the API
    t = threading.Thread(target=stream_worker.start, daemon=True)
    t.start()
    return {"status": "success", "message": "AI Engine started manually"}

@router.get("/recordings/list")
async def list_recorded_footage(current_user: User = Depends(get_current_user)):
    import os
    from app.config import settings
    files = []
    if os.path.exists(settings.RECORDINGS_DIR):
        for f in os.listdir(settings.RECORDINGS_DIR):
            if f.endswith(".mp4") or f.endswith(".avi") or f.endswith(".webm"):
                path = os.path.join(settings.RECORDINGS_DIR, f)
                files.append({
                    "filename": f,
                    "url": f"/recordings/{f}",
                    "size_bytes": os.path.getsize(path),
                    "created_at": os.path.getmtime(path)
                })
    return sorted(files, key=lambda x: x["created_at"], reverse=True)

