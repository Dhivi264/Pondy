from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db import get_db
from app.models.batch_job import ProcessingJob
from app.models.tracking import PersonSighting
from app.models.employee import Employee
from app.models.camera import Camera

router = APIRouter(tags=["Batch Processing"])

@router.get("/batch/jobs")
def get_batch_jobs(db: Session = Depends(get_db)):
    """Retrieve the status of all video processing jobs."""
    jobs = db.query(ProcessingJob).all()
    return {"jobs": [{
        "id": j.id,
        "filename": j.filename,
        "camera_name": j.camera_name,
        "status": j.status,
        "started_at": j.started_at,
        "completed_at": j.completed_at,
        "error_log": j.error_log
    } for j in jobs]}

@router.get("/batch/search")
def search_sightings(person_id: int = None, person_name: str = None, db: Session = Depends(get_db)):
    """7. SEARCH API
    Search for a person globally across all cameras and batch footage.
    """
    if not person_id and not person_name:
        raise HTTPException(status_code=400, detail="Provide person_id or person_name")
        
    query = db.query(PersonSighting, Employee, Camera).join(
        Employee, PersonSighting.employee_id == Employee.id
    ).join(
        Camera, PersonSighting.camera_id == Camera.id, isouter=True
    )
    
    if person_id:
        query = query.filter(Employee.id == person_id)
    if person_name:
        query = query.filter(Employee.name.ilike(f"%{person_name}%"))
        
    results = query.all()
    
    return {"matches": [{
        "person_id": e.id,
        "person_name": e.name,
        "camera_name": c.name if c else "Unknown Generic Camera",
        "first_seen": s.first_seen,
        "last_seen": s.last_seen,
        "total_visible_duration": s.duration_seconds,
        "snapshot_path": s.snapshot_path if hasattr(s, "snapshot_path") else None
    } for (s, e, c) in results]}
