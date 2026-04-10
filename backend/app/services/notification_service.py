import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models.camera import Camera
from app.models.notifications import (
    CameraHealthLog,
    NotificationAlert,
    SystemRecommendation,
    HealthCheckLog,
)
from app.repositories.notification_repository import (
    CameraHealthLogRepository,
    NotificationAlertRepository,
    SystemRecommendationRepository,
    HealthCheckLogRepository,
)
from app.repositories.camera_repository import CameraRepository

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for managing camera health notifications,
    analyzing failure patterns, and generating recommendations.
    """

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.health_repo = CameraHealthLogRepository(self.db)
        self.alert_repo = NotificationAlertRepository(self.db)
        self.recommendation_repo = SystemRecommendationRepository(self.db)
        self.scan_repo = HealthCheckLogRepository(self.db)
        self.camera_repo = CameraRepository(self.db)

    def log_camera_health(
        self,
        camera_id: int,
        status: str,
        uptime_percentage: float = 100.0,
        issue_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> CameraHealthLog:
        """Log camera health status"""
        try:
            log = CameraHealthLog(
                camera_id=camera_id,
                status=status,
                uptime_percentage=uptime_percentage,
                issue_type=issue_type,
                error_message=error_message,
                last_frame_time=datetime.utcnow() if status == "healthy" else None,
            )
            return self.health_repo.create(log)
        except Exception as e:
            logger.error(f"Error logging camera health: {e}")
            return None

    def analyze_camera_failure(self, camera_id: int) -> Dict:
        """
        Analyze failure patterns for a camera.
        Returns analysis with recommendations.
        """
        recent_logs = self.health_repo.get_recent_logs(camera_id, limit=20)
        failure_count_24h = self.health_repo.get_failure_count(camera_id, hours=24)
        recurring_issues = self.health_repo.get_recurring_issues(camera_id)

        if not recent_logs:
            return {"status": "no_data", "confidence": 0.0}

        # Calculate pattern score (0-1)
        failure_rate = failure_count_24h / 144  # 144 = 10-min scans in 24h
        pattern_score = min(failure_rate, 1.0)

        # Determine if issue is recurring
        is_recurring = len(recurring_issues) > 2

        # Get most common issue type
        issue_types = [log.issue_type for log in recent_logs if log.issue_type]
        most_common_issue = (
            max(set(issue_types), key=issue_types.count) if issue_types else "unknown"
        )

        analysis = {
            "camera_id": camera_id,
            "failure_count_24h": failure_count_24h,
            "pattern_score": pattern_score,
            "is_recurring": is_recurring,
            "most_common_issue": most_common_issue,
            "recent_logs": len(recent_logs),
            "confidence": min(pattern_score + 0.1 * len(recent_logs), 1.0),
        }

        return analysis

    def generate_alert(
        self,
        camera_id: Optional[int],
        alert_type: str,
        title: str,
        message: str,
        severity: str = "info",
        recommended_action: Optional[str] = None,
        confidence_score: float = 0.5,
    ) -> NotificationAlert:
        """Generate a new alert"""
        try:
            alert = NotificationAlert(
                camera_id=camera_id,
                alert_type=alert_type,
                title=title,
                message=message,
                severity=severity,
                recommended_action=recommended_action,
                confidence_score=confidence_score,
            )
            return self.alert_repo.create(alert)
        except Exception as e:
            logger.error(f"Error generating alert: {e}")
            return None

    def generate_recommendation(
        self,
        camera_id: Optional[int],
        category: str,
        title: str,
        description: str,
        based_on_patterns: Optional[str] = None,
        success_probability: float = 0.5,
        recommended_update: Optional[Dict] = None,
        apply_automatically: bool = False,
    ) -> SystemRecommendation:
        """Generate a system recommendation"""
        try:
            rec = SystemRecommendation(
                camera_id=camera_id,
                category=category,
                title=title,
                description=description,
                based_on_patterns=based_on_patterns,
                success_probability=success_probability,
                recommended_update=recommended_update,
                apply_automatically=apply_automatically,
            )
            return self.recommendation_repo.create(rec)
        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")
            return None

    def apply_auto_fix(
        self,
        alert_id: int,
        camera_id: int,
        fix_details: Dict,
    ) -> Tuple[bool, str]:
        """
        Apply automatic fix for an issue.
        Returns (success, message)
        """
        try:
            camera = self.camera_repo.get_by_id(camera_id)
            if not camera:
                return False, f"Camera {camera_id} not found"

            # Auto-fix strategies based on issue type
            if "offline" in fix_details.get("issue_type", "").lower():
                # Try to reconnect
                camera.status = "online"
                self.camera_repo.update(camera, {"status": "online"})
                logger.info(f"Auto-fix: Reconnected camera {camera_id}")
                return True, "Camera reconnection attempted"

            elif "fps_drop" in fix_details.get("issue_type", "").lower():
                # Reduce frame rate
                if camera.frame_rate > 5:
                    camera.frame_rate = max(camera.frame_rate - 5, 5)
                    self.camera_repo.update(camera, {"frame_rate": camera.frame_rate})
                    logger.info(f"Auto-fix: Reduced FPS for camera {camera_id} to {camera.frame_rate}")
                    return True, f"Frame rate reduced to {camera.frame_rate}"

            return False, "No applicable auto-fix for this issue"

        except Exception as e:
            logger.error(f"Error applying auto-fix: {e}")
            return False, str(e)

    def perform_health_check_scan(self) -> HealthCheckLog:
        """
        Perform a complete health check scan of all cameras.
        This is called every 10 minutes.
        """
        try:
            cameras = self.camera_repo.get_all()
            scan_results = {
                "total_cameras": len(cameras),
                "cameras_checked": 0,
                "cameras_online": 0,
                "cameras_offline": 0,
                "cameras_with_issues": 0,
                "details": [],
            }

            new_alerts = 0
            recommendations = 0
            auto_fixes = 0

            for camera in cameras:
                scan_results["cameras_checked"] += 1

                # Check camera status
                if camera.status == "online":
                    scan_results["cameras_online"] += 1
                    status = "healthy"
                else:
                    scan_results["cameras_offline"] += 1
                    status = "offline"
                    scan_results["cameras_with_issues"] += 1

                    # Generate offline alert
                    alert = self.generate_alert(
                        camera_id=camera.id,
                        alert_type="camera_offline",
                        title=f"Camera '{camera.name}' is Offline",
                        message=f"Camera at {camera.location} has gone offline. Stream unavailable.",
                        severity="critical",
                        recommended_action="Check camera connection and power supply",
                        confidence_score=0.95,
                    )
                    if alert:
                        new_alerts += 1

                # Log health
                self.log_camera_health(
                    camera_id=camera.id,
                    status=status,
                    uptime_percentage=100.0 if status == "healthy" else 0.0,
                )

                # Analyze patterns
                analysis = self.analyze_camera_failure(camera.id)

                if analysis.get("confidence", 0) > 0.7:
                    scan_results["cameras_with_issues"] += 1

                    # Generate recommendation
                    rec = self.generate_recommendation(
                        camera_id=camera.id,
                        category="optimization",
                        title=f"Performance Issue Detected - {camera.name}",
                        description=f"Camera shows recurring {analysis.get('most_common_issue', 'unknown')} issues. "
                        f"Pattern confidence: {analysis.get('confidence', 0):.1%}",
                        based_on_patterns=str(analysis),
                        success_probability=0.7,
                        apply_automatically=False,
                    )
                    if rec:
                        recommendations += 1

                    scan_results["details"].append(
                        {
                            "camera_id": camera.id,
                            "camera_name": camera.name,
                            "analysis": analysis,
                        }
                    )

            # Create health check log
            scan_log = HealthCheckLog(
                scan_timestamp=datetime.utcnow(),
                total_cameras=scan_results["total_cameras"],
                cameras_online=scan_results["cameras_online"],
                cameras_offline=scan_results["cameras_offline"],
                cameras_with_issues=scan_results["cameras_with_issues"],
                new_alerts_generated=new_alerts,
                recommendations_generated=recommendations,
                auto_fixes_applied=auto_fixes,
                scan_results=scan_results,
            )

            self.scan_repo.create(scan_log)

            logger.info(
                f"[HealthCheck] Scan complete: {scan_results['cameras_online']}/{scan_results['total_cameras']} online, "
                f"{new_alerts} alerts, {recommendations} recommendations"
            )

            return scan_log

        except Exception as e:
            logger.error(f"Error during health check scan: {e}")
            return None

    def get_system_health_summary(self) -> Dict:
        """Get overall system health summary"""
        try:
            cameras = self.camera_repo.get_all()
            unread_alerts = self.alert_repo.get_unread_alerts()
            active_recs = self.recommendation_repo.get_active_recommendations(limit=100)
            recent_scan = self.scan_repo.get_recent_scans(limit=1)

            summary = {
                "total_cameras": len(cameras),
                "online_cameras": len([c for c in cameras if c.status == "online"]),
                "offline_cameras": len([c for c in cameras if c.status == "offline"]),
                "critical_alerts": len(
                    [a for a in unread_alerts if a.severity == "critical"]
                ),
                "warning_alerts": len(
                    [a for a in unread_alerts if a.severity == "warning"]
                ),
                "active_recommendations": len(active_recs),
                "last_scan": recent_scan[0] if recent_scan else None,
            }
            return summary
        except Exception as e:
            logger.error(f"Error getting system health summary: {e}")
            return {}

    def get_camera_health_details(self, camera_id: int) -> Dict:
        """Get detailed health info for a camera"""
        try:
            camera = self.camera_repo.get_by_id(camera_id)
            if not camera:
                return {}

            recent_logs = self.health_repo.get_recent_logs(camera_id, limit=10)
            alerts = self.alert_repo.get_camera_alerts(camera_id, limit=10)
            recommendations = self.recommendation_repo.get_camera_recommendations(
                camera_id, limit=10
            )

            return {
                "camera_id": camera_id,
                "camera_name": camera.name,
                "current_status": camera.status,
                "location": camera.location,
                "recent_health_logs": [
                    {
                        "id": log.id,
                        "status": log.status,
                        "uptime_percentage": log.uptime_percentage,
                        "issue_type": log.issue_type,
                        "timestamp": log.created_at,
                    }
                    for log in recent_logs
                ],
                "active_alerts": [
                    {
                        "id": alert.id,
                        "type": alert.alert_type,
                        "title": alert.title,
                        "severity": alert.severity,
                        "is_read": alert.is_read,
                        "created_at": alert.created_at,
                    }
                    for alert in alerts
                ],
                "recommendations": [
                    {
                        "id": rec.id,
                        "category": rec.category,
                        "title": rec.title,
                        "success_probability": rec.success_probability,
                        "is_applied": rec.is_applied,
                        "created_at": rec.created_at,
                    }
                    for rec in recommendations
                ],
            }
        except Exception as e:
            logger.error(f"Error getting camera health details: {e}")
            return {}

    def close(self):
        """Close database session"""
        if self.db:
            self.db.close()
