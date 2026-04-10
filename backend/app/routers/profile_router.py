from fastapi import APIRouter, Depends
from app.deps import get_current_user
from app.schemas import UserProfileResponse
from app.repositories.profile_repository import ProfileRepository
from app.services.profile_service import ProfileService
import pyodbc
from app.access_db import get_db_connection

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me", response_model=UserProfileResponse)
def get_profile(
    current_user: dict = Depends(get_current_user),
    db: pyodbc.Connection = Depends(get_db_connection),
):
    repo = ProfileRepository(db)
    service = ProfileService(repo)
    return service.get_profile(current_user)
