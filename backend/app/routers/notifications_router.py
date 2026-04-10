from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth import get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService
from app.schemas_notifications import (
    NotificationAlertResponse,
    NotificationAlertUpdate,
    SystemRecommendationResponse,
    SystemRecommendationUpdate,
    HealthCheckLogResponse,
    SystemHealthSummary,
    CameraDetailedHealth,
)

router = APIRouter(tags=["Notifications"])


@router.get("/notifications/health-summary", response_model=SystemHealthSummary)
async def get_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get overall system health summary"""
    service = NotificationService(db)
    try:
        summary = service.get_system_health_summary()
        return SystemHealthSummary(**summary)
    finally:
        service.close()


@router.get("/notifications/camera/{camera_id}/health", response_model=CameraDetailedHealth)
async def get_camera_health(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed health info for a camera"""
    service = NotificationService(db)
    try:
        health = service.get_camera_health_details(camera_id)
        if not health:
            raise HTTPException(status_code=404, detail="Camera not found")
        return CameraDetailedHealth(**health)
    finally:
        service.close()


@router.get("/notifications/alerts", response_model=List[NotificationAlertResponse])
async def list_alerts(
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List alerts, optionally filtered to unread only"""
    service = NotificationService(db)
    try:
        if unread_only:
            alerts = service.alert_repo.get_unread_alerts()[:limit]
        else:
            alerts = service.alert_repo.get_unresolved_alerts(limit=limit)

        return [
            NotificationAlertResponse(
                id=a.id,
                camera_id=a.camera_id,
                alert_type=a.alert_type,
                title=a.title,
                message=a.message,
                severity=a.severity,
                recommended_action=a.recommended_action,
                is_read=a.is_read,
                is_resolved=a.is_resolved,
                auto_fix_applied=a.auto_fix_applied,
                auto_fix_details=a.auto_fix_details,
                confidence_score=a.confidence_score,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in alerts
        ]
    finally:
        service.close()


@router.get("/notifications/alerts/camera/{camera_id}", response_model=List[NotificationAlertResponse])
async def get_camera_alerts(
    camera_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get alerts for a specific camera"""
    service = NotificationService(db)
    try:
        alerts = service.alert_repo.get_camera_alerts(camera_id, limit=limit)
        return [
            NotificationAlertResponse(
                id=a.id,
                camera_id=a.camera_id,
                alert_type=a.alert_type,
                title=a.title,
                message=a.message,
                severity=a.severity,
                recommended_action=a.recommended_action,
                is_read=a.is_read,
                is_resolved=a.is_resolved,
                auto_fix_applied=a.auto_fix_applied,
                auto_fix_details=a.auto_fix_details,
                confidence_score=a.confidence_score,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in alerts
        ]
    finally:
        service.close()


@router.put("/notifications/alerts/{alert_id}", response_model=NotificationAlertResponse)
async def update_alert(
    alert_id: int,
    update: NotificationAlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update alert (mark as read/resolved)"""
    service = NotificationService(db)
    try:
        alert = service.alert_repo.get_by_id(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        if update.is_read is not None:
            alert.is_read = update.is_read
        if update.is_resolved is not None:
            alert.is_resolved = update.is_resolved

        updated = service.alert_repo.update(alert, update.dict(exclude_unset=True))

        return NotificationAlertResponse(
            id=updated.id,
            camera_id=updated.camera_id,
            alert_type=updated.alert_type,
            title=updated.title,
            message=updated.message,
            severity=updated.severity,
            recommended_action=updated.recommended_action,
            is_read=updated.is_read,
            is_resolved=updated.is_resolved,
            auto_fix_applied=updated.auto_fix_applied,
            auto_fix_details=updated.auto_fix_details,
            confidence_score=updated.confidence_score,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )
    finally:
        service.close()


@router.get("/notifications/recommendations", response_model=List[SystemRecommendationResponse])
async def list_recommendations(
    active_only: bool = True,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List system recommendations"""
    service = NotificationService(db)
    try:
        if active_only:
            recs = service.recommendation_repo.get_active_recommendations(limit=limit)
        else:
            recs = service.recommendation_repo.get_all(limit=limit)

        return [
            SystemRecommendationResponse(
                id=r.id,
                camera_id=r.camera_id,
                category=r.category,
                title=r.title,
                description=r.description,
                based_on_patterns=r.based_on_patterns,
                success_probability=r.success_probability,
                recommended_update=r.recommended_update,
                apply_automatically=r.apply_automatically,
                is_applied=r.is_applied,
                is_read=r.is_read,
                is_dismissed=r.is_dismissed,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in recs
        ]
    finally:
        service.close()


@router.get("/notifications/recommendations/camera/{camera_id}", response_model=List[SystemRecommendationResponse])
async def get_camera_recommendations(
    camera_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recommendations for a specific camera"""
    service = NotificationService(db)
    try:
        recs = service.recommendation_repo.get_camera_recommendations(
            camera_id, limit=limit
        )
        return [
            SystemRecommendationResponse(
                id=r.id,
                camera_id=r.camera_id,
                category=r.category,
                title=r.title,
                description=r.description,
                based_on_patterns=r.based_on_patterns,
                success_probability=r.success_probability,
                recommended_update=r.recommended_update,
                apply_automatically=r.apply_automatically,
                is_applied=r.is_applied,
                is_read=r.is_read,
                is_dismissed=r.is_dismissed,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in recs
        ]
    finally:
        service.close()


@router.put(
    "/notifications/recommendations/{recommendation_id}/apply",
    response_model=SystemRecommendationResponse,
)
async def apply_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply a recommendation"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    service = NotificationService(db)
    try:
        rec = service.recommendation_repo.mark_as_applied(recommendation_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        return SystemRecommendationResponse(
            id=rec.id,
            camera_id=rec.camera_id,
            category=rec.category,
            title=rec.title,
            description=rec.description,
            based_on_patterns=rec.based_on_patterns,
            success_probability=rec.success_probability,
            recommended_update=rec.recommended_update,
            apply_automatically=rec.apply_automatically,
            is_applied=rec.is_applied,
            is_read=rec.is_read,
            is_dismissed=rec.is_dismissed,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
        )
    finally:
        service.close()


@router.put(
    "/notifications/recommendations/{recommendation_id}/dismiss",
    response_model=SystemRecommendationResponse,
)
async def dismiss_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismiss a recommendation"""
    service = NotificationService(db)
    try:
        rec = service.recommendation_repo.mark_as_dismissed(recommendation_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        return SystemRecommendationResponse(
            id=rec.id,
            camera_id=rec.camera_id,
            category=rec.category,
            title=rec.title,
            description=rec.description,
            based_on_patterns=rec.based_on_patterns,
            success_probability=rec.success_probability,
            recommended_update=rec.recommended_update,
            apply_automatically=rec.apply_automatically,
            is_applied=rec.is_applied,
            is_read=rec.is_read,
            is_dismissed=rec.is_dismissed,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
        )
    finally:
        service.close()


@router.get("/notifications/scans", response_model=List[HealthCheckLogResponse])
async def list_health_scans(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent health check scans"""
    service = NotificationService(db)
    try:
        scans = service.scan_repo.get_recent_scans(limit=limit)
        return [
            HealthCheckLogResponse(
                id=s.id,
                scan_timestamp=s.scan_timestamp,
                total_cameras=s.total_cameras,
                cameras_online=s.cameras_online,
                cameras_offline=s.cameras_offline,
                cameras_with_issues=s.cameras_with_issues,
                new_alerts_generated=s.new_alerts_generated,
                recommendations_generated=s.recommendations_generated,
                auto_fixes_applied=s.auto_fixes_applied,
                scan_results=s.scan_results,
                created_at=s.created_at,
            )
            for s in scans
        ]
    finally:
        service.close()


@router.post("/notifications/scan-now", response_model=HealthCheckLogResponse)
async def trigger_health_scan_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger a health scan (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    service = NotificationService(db)
    try:
        scan_log = service.perform_health_check_scan()
        if not scan_log:
            raise HTTPException(status_code=500, detail="Health scan failed")

        return HealthCheckLogResponse(
            id=scan_log.id,
            scan_timestamp=scan_log.scan_timestamp,
            total_cameras=scan_log.total_cameras,
            cameras_online=scan_log.cameras_online,
            cameras_offline=scan_log.cameras_offline,
            cameras_with_issues=scan_log.cameras_with_issues,
            new_alerts_generated=scan_log.new_alerts_generated,
            recommendations_generated=scan_log.recommendations_generated,
            auto_fixes_applied=scan_log.auto_fixes_applied,
            scan_results=scan_log.scan_results,
            created_at=scan_log.created_at,
        )
    finally:
        service.close()
