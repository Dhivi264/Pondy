from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from app.db import Base


class CameraHealthLog(Base):
    """Track camera health metrics and failures over time"""
    __tablename__ = "camera_health_logs"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    
    # Health metrics
    status = Column(String, default="healthy")  # healthy, warning, critical, offline
    uptime_percentage = Column(Float, default=100.0)
    last_frame_time = Column(DateTime(timezone=True), nullable=True)
    failure_count = Column(Integer, default=0)
    recovery_time_seconds = Column(Integer, default=0)
    
    # Issues detected
    issue_type = Column(String, nullable=True)  # connection, fps_drop, blur, etc
    error_message = Column(String, nullable=True)
    
    # Learning data
    is_recurring_issue = Column(Boolean, default=False)
    pattern_score = Column(Float, default=0.0)  # 0-1: how predictable this failure is
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class NotificationAlert(Base):
    """System notifications and alerts for admins"""
    __tablename__ = "notification_alerts"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    
    # Alert details
    alert_type = Column(String, nullable=False)  # failure_detected, pattern_warning, config_needed, etc
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    severity = Column(String, default="info")  # info, warning, critical
    
    # Recommendation
    recommended_action = Column(String, nullable=True)
    auto_fix_applied = Column(Boolean, default=False)
    auto_fix_details = Column(JSON, nullable=True)
    
    # Status
    is_read = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    
    # Learning metadata
    confidence_score = Column(Float, default=0.0)  # 0-1: how confident the system is
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SystemRecommendation(Base):
    """AI-generated recommendations for system updates and optimizations"""
    __tablename__ = "system_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    
    # Recommendation details
    category = Column(String, nullable=False)  # config, settings, firmware, bugfix, optimization
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    
    # Learning data
    based_on_patterns = Column(String, nullable=True)  # JSON: failure patterns analyzed
    success_probability = Column(Float, default=0.0)  # 0-1: estimated success rate
    
    # Action
    recommended_update = Column(JSON, nullable=True)  # JSON: what settings to change
    apply_automatically = Column(Boolean, default=False)
    is_applied = Column(Boolean, default=False)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class HealthCheckLog(Base):
    """Track every 10-minute health check scan"""
    __tablename__ = "health_check_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Scan details
    scan_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    total_cameras = Column(Integer, default=0)
    cameras_online = Column(Integer, default=0)
    cameras_offline = Column(Integer, default=0)
    cameras_with_issues = Column(Integer, default=0)
    
    # Analysis results
    new_alerts_generated = Column(Integer, default=0)
    recommendations_generated = Column(Integer, default=0)
    auto_fixes_applied = Column(Integer, default=0)
    
    # Scan results
    scan_results = Column(JSON, nullable=True)  # Detailed scan data
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
