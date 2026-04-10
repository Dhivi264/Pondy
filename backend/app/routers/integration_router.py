from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.db import get_db
from app.auth import get_current_user
from app.services.integration_service import IntegrationService
from app.schemas import SyncResponse
from app.models.user import User

router = APIRouter(prefix="/integrations/accdb", tags=["Integrations"])


@router.post("/import-employees", response_model=SyncResponse)
async def import_employees(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    service = IntegrationService(db)
    count = service.sync_employees_from_accdb()
    return {
        "items_synced": count,
        "message": f"Successfully imported {count} new employees from MS Access.",
    }


@router.post("/export-attendance", response_model=SyncResponse)
async def export_attendance(
    attendance_date: date = date.today(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    service = IntegrationService(db)
    count = service.sync_attendance_to_accdb(attendance_date)
    return {
        "items_synced": count,
        "message": f"Successfully exported {count} attendance records to MS Access.",
    }
