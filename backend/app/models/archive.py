from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.db import Base


class ArchiveRecord(Base):
    """Metadata for saved snapshots and video clips."""

    __tablename__ = "archive_records"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)

    event_type = Column(String, nullable=False)  # entry, exit, anomaly, manual
    title = Column(String, nullable=True)

    file_path = Column(String, nullable=False)
    thumbnail_path = Column(String, nullable=True)

    duration_seconds = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
