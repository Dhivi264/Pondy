from fastapi import APIRouter, Depends
from typing import List, Optional
import pyodbc
from app.access_db import get_db_connection
from app.schemas import ArchiveResponse
from app.repositories.archive_repository import ArchiveRepository
from app.services.archive_service import ArchiveService
from app.deps import get_current_user

router = APIRouter(
    prefix="/archive", tags=["Archive"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=List[ArchiveResponse])
def get_archives(
    record_type: Optional[str] = None,
    db: pyodbc.Connection = Depends(get_db_connection),
):
    repo = ArchiveRepository(db)
    service = ArchiveService(repo)
    return service.get_archives(record_type)
