from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from app.db import Base


class AttendanceSession(Base):
    """Daily check-in/out session for an employee."""

    __tablename__ = "attendance_sessions"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    attendance_date = Column(Date, nullable=False, index=True)

    entry_time = Column(DateTime(timezone=True), nullable=True)
    exit_time = Column(DateTime(timezone=True), nullable=True)

    entry_camera_id = Column(Integer, nullable=True)
    exit_camera_id = Column(Integer, nullable=True)

    entry_clip_path = Column(String, nullable=True)
    exit_clip_path = Column(String, nullable=True)

    cameras_spotted_count = Column(Integer, default=0)
    total_visible_duration_seconds = Column(Integer, default=0)

    attendance_status = Column(
        String, default="absent"
    )  # present, late, absent, half-day
    confidence_summary = Column(Float, default=0.0)  # Average face confidence

    # --- Anomaly Analytics (Trend 2026) ---
    loitering_flag = Column(Integer, default=0)  # 1 if suspicious dwelling detected
    last_anomaly_detected = Column(DateTime(timezone=True), nullable=True)
    total_suspicious_duration = Column(Integer, default=0)  # Seconds spent loitering
    # -------------------------------------

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CameraPresenceSummary(Base):
    """Daily summary of how long an employee was seen by each camera."""

    __tablename__ = "camera_presence_summaries"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    attendance_date = Column(Date, nullable=False, index=True)

    total_visible_seconds = Column(Integer, default=0)
    sightings_count = Column(Integer, default=0)

    first_seen = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
