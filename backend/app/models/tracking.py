from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base


class TrackEvent(Base):
    __tablename__ = "track_events"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    track_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Bounding Box
    bbox_x1 = Column(Float)
    bbox_y1 = Column(Float)
    bbox_x2 = Column(Float)
    bbox_y2 = Column(Float)

    confidence = Column(Float)
    zone_id = Column(String, nullable=True)


class PersonSighting(Base):
    """Summarized sighting of a person by a camera in one continuous session."""

    __tablename__ = "person_sightings"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    track_id = Column(Integer, nullable=False)

    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Integer, default=0)

    confidence_score = Column(Float, default=0.0)
    snapshot_path = Column(String, nullable=True)
    clip_path = Column(String, nullable=True)

    employee = relationship("Employee", back_populates="sightings")
