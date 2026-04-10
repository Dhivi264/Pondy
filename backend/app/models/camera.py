from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from sqlalchemy.sql import func
from app.db import Base


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    channel_no = Column(Integer, nullable=True)
    location = Column(String, nullable=True)
    status = Column(String, default="online")  # online, offline, error
    frame_rate = Column(Integer, default=15)
    stream_url = Column(String, nullable=False)
    is_entry_camera = Column(Boolean, default=False)
    is_exit_camera = Column(Boolean, default=False)

    # JSON field for zone configurations (polygons, IDs, etc.)
    zone_config = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
