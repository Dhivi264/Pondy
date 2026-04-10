from sqlalchemy import Column, Integer, String, Float
from app.db import Base


class SystemSettings(Base):
    """Global AI and business logic configuration stored in DB."""

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    face_match_threshold = Column(Float, default=0.6)
    duplicate_window_seconds = Column(Integer, default=30)
    clip_pre_seconds = Column(Integer, default=5)
    clip_post_seconds = Column(Integer, default=5)
    attendance_mode = Column(String, default="auto")  # auto, manual, hybrid
    inference_interval_ms = Column(Integer, default=100)
