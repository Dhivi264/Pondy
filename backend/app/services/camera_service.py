from typing import List, Optional
from app.repositories.camera_repository import CameraRepository
from app.schemas import CameraResponse


class CameraService:
    def __init__(self, repo: CameraRepository):
        self.repo = repo

    def get_all_cameras(self, search: Optional[str]) -> List[CameraResponse]:
        return self.repo.get_all(search)
