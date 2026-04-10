from sqlalchemy import Column, Integer, String, DateTime, Float
from datetime import datetime
from app.db import Base

class DeliveryPackage(Base):
    """
    Model for tracking physical delivery packages (boxes, parcels) detected by the CCTV.
    """
    __tablename__ = "delivery_packages"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, index=True)
    status = Column(String(50), default="detected")  # e.g., 'detected', 'retrieved'
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    thumbnail_path = Column(String(500), nullable=True)
    confidence = Column(Float, default=0.0)
    location_box = Column(String(100), nullable=True) # JSON coordinates
