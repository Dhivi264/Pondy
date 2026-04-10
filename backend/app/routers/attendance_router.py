from typing import List
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth import get_current_user
from app.repositories.attendance_repository import AttendanceRepository
from app.schemas import AttendanceSessionResponse
from app.models.user import User

router = APIRouter(tags=["Attendance"])


@router.get("/", response_model=List[AttendanceSessionResponse])
async def get_attendance(
    attendance_date: date = date.today(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = AttendanceRepository(db)
    return repo.get_sessions_by_date(attendance_date)


@router.get("/{employee_id}/daily", response_model=AttendanceSessionResponse)
async def get_employee_attendance(
    employee_id: int,
    attendance_date: date = date.today(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = AttendanceRepository(db)
    session = repo.get_employee_daily_session(employee_id, attendance_date)
    return session


from app.schemas import AttendanceSummaryStats


@router.get("/summary/stats", response_model=AttendanceSummaryStats)
async def get_attendance_stats(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    from app.services.dashboard_service import DashboardService

    service = DashboardService(db)
    summary = service.get_summary()
    return {
        "total_employees": summary["employees"],
        "present_today": summary["present_today"],
        "absent_today": summary["absent_today"],
        "total_cameras": summary["total_cameras"],
        "active_cameras": summary["active_cameras"],
        "avg_ai_latency_ms": summary["avg_ai_latency_ms"],
        "global_ai_fps": summary["global_ai_fps"],
    }
