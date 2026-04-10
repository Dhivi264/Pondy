import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # API Settings
    APP_NAME: str = "Smart CCTV Production Backend"
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Primary Database (SQLite/PostgreSQL)
    DATABASE_URL: str = "sqlite:///./production.db"

    # AI Model Settings
    @property
    def AI_DEVICE(self) -> str:
        """Auto-detect CUDA if available, fallback to CPU."""
        import torch
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    DETECTOR_MODEL: str = "yolo11s.pt"  # Upgraded to YOLOv11 small for better accuracy
    YOLO_FACE_MODEL: str = (
        "models/yolo_face/yolov11n-face.pt"  # Face-tuned YOLO11 weight
    )
    TRACKER_TYPE: str = "bytetrack"  # bytetrack or botsort
    FACE_MODEL_DIR: str = "models/yolo_face"  # Directory for face weights & ONNX head
    FACE_MATCH_THRESHOLD: float = 0.55
    FACE_RECOGNITION_COOLDOWN_SECONDS: int = 30

    # Video Pipeline Settings
    CLIP_PRE_SECONDS: int = 5
    CLIP_POST_SECONDS: int = 5
    RECORDINGS_DIR: str = "data/recordings"
    FACES_DIR: str = "data/faces"
    CAPTURED_FACES_DIR: str = "data/captured_faces"

    # Server Settings
    CORS_ORIGINS: List[str] = ["*"]

    # Advanced AI Analytics Settings (2026 Trends)
    LOITERING_THRESHOLD_SECONDS: int = 300  # 5 minutes
    DANGER_ZONE_THRESHOLD_SECONDS: int = 30  # 30 seconds for loitering in restricted areas
    ENABLE_PRIVACY_BLUR: bool = False  # Disabled — face blur prevents recognition; enable only for public view

    # Push Notification Settings
    SMTP_HOST: str = ""        # e.g. "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    ADMIN_EMAIL: str = ""

    # Resource Limits
    MAX_ACTIVE_CAMERAS: int = 32     # Limit simultaneous AI processing for stability
    MAX_TOTAL_CAMERAS: int = 500    # Total DB limit for camera registrations
    GLOBAL_FRAME_SKIP: int = 2      # Skip every N frames to reduce CPU/GPU load

    class Config:
        env_file = ".env"


settings = Settings()
