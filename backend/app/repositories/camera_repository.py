from typing import List
from sqlalchemy.orm import Session
from app.models.camera import Camera
from app.repositories.base_repository import BaseRepository


class CameraRepository(BaseRepository[Camera]):
    def __init__(self, db: Session):
        super().__init__(Camera, db)

    def get_online_cameras(self) -> List[Camera]:
        return self.db.query(Camera).filter(Camera.status == "online").all()

    def update_status(self, camera_id: int, status: str):
        camera = self.get_by_id(camera_id)
        if camera:
            camera.status = status
            self.db.commit()
