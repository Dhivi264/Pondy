from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.attendance import AttendanceSession, CameraPresenceSummary
from app.models.employee import Employee
from app.models.camera import Camera
from typing import List, Optional
from datetime import datetime

router = APIRouter(tags=["Analytics & Search"])

@router.get("/search")
def search_person(
    person_id: Optional[str] = Query(None, description="Employee code/ID"),
    name: Optional[str] = Query(None, description="Part of person name"),
    db: Session = Depends(get_db)
):
    """
    STRICT REQUIREMENT 7: Search by person ID or name.
    """
    query = db.query(Employee)
    if person_id:
        query = query.filter(Employee.employee_id == person_id)
    if name:
        query = query.filter(Employee.name.ilike(f"%{name}%"))
    
    employees = query.all()
    results = []

    for emp in employees:
        # Get individual camera sighting summaries for this employee
        summaries = db.query(CameraPresenceSummary, Camera.name)\
            .join(Camera, Camera.id == CameraPresenceSummary.camera_id)\
            .filter(CameraPresenceSummary.employee_id == emp.id)\
            .order_by(CameraPresenceSummary.last_seen.desc())\
            .all()
        
        camera_logs = []
        for s, cam_name in summaries:
            camera_logs.append({
                "camera_name": cam_name,
                "first_seen": s.first_seen,
                "last_seen": s.last_seen,
                "duration_seconds": s.total_visible_seconds,
                "sightings_count": s.sightings_count
            })

        results.append({
            "person_id": emp.employee_id,
            "name": emp.name,
            "department": emp.department,
            "total_duration_today": sum(c["duration_seconds"] for c in camera_logs),
            "camera_trail": camera_logs
        })

    return results

@router.get("/logs")
def get_all_logs(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """STRICT REQUIREMENT 8: Return all sightings/attendance logs."""
    logs = db.query(AttendanceSession).order_by(AttendanceSession.attendance_date.desc()).limit(limit).all()
    
    return [
        {
            "id": l.id,
            "employee_db_id": l.employee_id,
            "date": l.attendance_date,
            "first_seen": l.entry_time,
            "last_seen": l.exit_time,
            "status": l.attendance_status,
            "duration": f"{l.total_visible_duration_seconds}s"
        }
        for l in logs
    ]
