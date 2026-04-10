from fastapi import APIRouter, Depends
from app.schemas import SettingsResponse
from app.repositories.settings_repository import SettingsRepository
from app.services.settings_service import SettingsService
from app.deps import get_current_user
import pyodbc
from app.access_db import get_db_connection

router = APIRouter(
    prefix="/settings", tags=["Settings"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=SettingsResponse)
def get_settings(db: pyodbc.Connection = Depends(get_db_connection)):
    repo = SettingsRepository(db)
    service = SettingsService(repo)
    return service.get_settings()
