from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
import datetime
from app.db import Base

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    file_path = Column(String)
    camera_name = Column(String, nullable=True) # Mapped from filename
    status = Column(String, default="pending")  # pending, processing, completed, failed
    error_log = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
