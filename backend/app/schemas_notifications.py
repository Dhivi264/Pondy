from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── Camera Health Log Schemas ──────────────────────────────────

class CameraHealthLogBase(BaseModel):
    camera_id: int
    status: Optional[str] = "healthy"
    uptime_percentage: Optional[float] = 100.0
    failure_count: Optional[int] = 0
    issue_type: Optional[str] = None
    error_message: Optional[str] = None
    is_recurring_issue: Optional[bool] = False
    pattern_score: Optional[float] = 0.0


class CameraHealthLogCreate(CameraHealthLogBase):
    pass


class CameraHealthLogResponse(CameraHealthLogBase):
    id: int
    last_frame_time: Optional[datetime]
    recovery_time_seconds: Optional[int]
    created_at: datetime
    timestamp: datetime

    class Config:
        from_attributes = True


# ── Notification Alert Schemas ────────────────────────────────

class NotificationAlertBase(BaseModel):
    camera_id: Optional[int] = None
    alert_type: str
    title: str
    message: str
    severity: Optional[str] = "info"
    recommended_action: Optional[str] = None


class NotificationAlertCreate(NotificationAlertBase):
    auto_fix_applied: Optional[bool] = False
    confidence_score: Optional[float] = 0.0


class NotificationAlertResponse(NotificationAlertBase):
    id: int
    is_read: bool
    is_resolved: bool
    auto_fix_applied: bool
    auto_fix_details: Optional[Dict[str, Any]]
    confidence_score: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationAlertUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_resolved: Optional[bool] = None


# ── System Recommendation Schemas ─────────────────────────────

class SystemRecommendationBase(BaseModel):
    camera_id: Optional[int] = None
    category: str
    title: str
    description: str


class SystemRecommendationCreate(SystemRecommendationBase):
    based_on_patterns: Optional[str] = None
    success_probability: Optional[float] = 0.0
    recommended_update: Optional[Dict[str, Any]] = None
    apply_automatically: Optional[bool] = False


class SystemRecommendationResponse(SystemRecommendationBase):
    id: int
    based_on_patterns: Optional[str]
    success_probability: float
    recommended_update: Optional[Dict[str, Any]]
    apply_automatically: bool
    is_applied: bool
    is_read: bool
    is_dismissed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemRecommendationUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_dismissed: Optional[bool] = None


# ── Health Check Log Schemas ──────────────────────────────────

class HealthCheckLogBase(BaseModel):
    total_cameras: Optional[int] = 0
    cameras_online: Optional[int] = 0
    cameras_offline: Optional[int] = 0
    cameras_with_issues: Optional[int] = 0
    new_alerts_generated: Optional[int] = 0
    recommendations_generated: Optional[int] = 0
    auto_fixes_applied: Optional[int] = 0


class HealthCheckLogCreate(HealthCheckLogBase):
    scan_results: Optional[Dict[str, Any]] = None


class HealthCheckLogResponse(HealthCheckLogBase):
    id: int
    scan_timestamp: datetime
    scan_results: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Summary Schemas ──────────────────────────────────────────

class SystemHealthSummary(BaseModel):
    """Overall system health at a glance"""
    total_cameras: int
    online_cameras: int
    offline_cameras: int
    critical_alerts: int
    warning_alerts: int
    recommended_actions: int
    recent_scan: Optional[HealthCheckLogResponse]


class CameraDetailedHealth(BaseModel):
    """Detailed health info for a specific camera"""
    camera_id: int
    camera_name: Optional[str]
    current_status: str
    uptime_percentage: float
    recent_issues: List[CameraHealthLogResponse]
    active_alerts: List[NotificationAlertResponse]
    recommendations: List[SystemRecommendationResponse]
