from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.notifications import CameraHealthLog, NotificationAlert, SystemRecommendation, HealthCheckLog
from app.repositories.base_repository import BaseRepository


class CameraHealthLogRepository(BaseRepository[CameraHealthLog]):
    def __init__(self, db: Session):
        super().__init__(CameraHealthLog, db)

    def get_recent_logs(self, camera_id: int, limit: int = 10):
        """Get recent health logs for a specific camera"""
        return self.db.query(CameraHealthLog).filter(
            CameraHealthLog.camera_id == camera_id
        ).order_by(CameraHealthLog.created_at.desc()).limit(limit).all()

    def get_failure_count(self, camera_id: int, hours: int = 24):
        """Count failures in past N hours"""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return self.db.query(CameraHealthLog).filter(
            CameraHealthLog.camera_id == camera_id,
            CameraHealthLog.status != "healthy",
            CameraHealthLog.created_at >= cutoff
        ).count()

    def get_recurring_issues(self, camera_id: int):
        """Get all identified recurring issues for a camera"""
        return self.db.query(CameraHealthLog).filter(
            CameraHealthLog.camera_id == camera_id,
            CameraHealthLog.is_recurring_issue == True
        ).all()


class NotificationAlertRepository(BaseRepository[NotificationAlert]):
    def __init__(self, db: Session):
        super().__init__(NotificationAlert, db)

    def get_unread_alerts(self):
        """Get all unread alerts ordered by severity"""
        severity_order = {"critical": 3, "warning": 2, "info": 1}
        alerts = self.db.query(NotificationAlert).filter(
            NotificationAlert.is_read == False
        ).all()
        return sorted(alerts, key=lambda x: severity_order.get(x.severity, 0), reverse=True)

    def get_unresolved_alerts(self, limit: int = 50):
        """Get unresolved alerts"""
        return self.db.query(NotificationAlert).filter(
            NotificationAlert.is_resolved == False
        ).order_by(NotificationAlert.created_at.desc()).limit(limit).all()

    def get_camera_alerts(self, camera_id: int, limit: int = 20):
        """Get alerts for a specific camera"""
        return self.db.query(NotificationAlert).filter(
            NotificationAlert.camera_id == camera_id
        ).order_by(NotificationAlert.created_at.desc()).limit(limit).all()

    def get_alerts_by_type(self, alert_type: str, limit: int = 50):
        """Get alerts of specific type"""
        return self.db.query(NotificationAlert).filter(
            NotificationAlert.alert_type == alert_type
        ).order_by(NotificationAlert.created_at.desc()).limit(limit).all()

    def mark_as_read(self, alert_id: int):
        """Mark alert as read"""
        alert = self.get_by_id(alert_id)
        if alert:
            alert.is_read = True
            self.db.commit()
            return alert
        return None

    def mark_as_resolved(self, alert_id: int):
        """Mark alert as resolved"""
        alert = self.get_by_id(alert_id)
        if alert:
            alert.is_resolved = True
            self.db.commit()
            return alert
        return None


class SystemRecommendationRepository(BaseRepository[SystemRecommendation]):
    def __init__(self, db: Session):
        super().__init__(SystemRecommendation, db)

    def get_active_recommendations(self, limit: int = 50):
        """Get recommendations that haven't been applied or dismissed"""
        return self.db.query(SystemRecommendation).filter(
            SystemRecommendation.is_applied == False,
            SystemRecommendation.is_dismissed == False
        ).order_by(SystemRecommendation.success_probability.desc()).limit(limit).all()

    def get_camera_recommendations(self, camera_id: int, limit: int = 20):
        """Get recommendations for a specific camera"""
        return self.db.query(SystemRecommendation).filter(
            SystemRecommendation.camera_id == camera_id
        ).order_by(SystemRecommendation.created_at.desc()).limit(limit).all()

    def get_recommendations_by_category(self, category: str, limit: int = 50):
        """Get recommendations by category"""
        return self.db.query(SystemRecommendation).filter(
            SystemRecommendation.category == category
        ).order_by(SystemRecommendation.success_probability.desc()).limit(limit).all()

    def mark_as_applied(self, recommendation_id: int):
        """Mark recommendation as applied"""
        from datetime import datetime
        rec = self.get_by_id(recommendation_id)
        if rec:
            rec.is_applied = True
            rec.applied_at = datetime.utcnow()
            self.db.commit()
            return rec
        return None

    def mark_as_dismissed(self, recommendation_id: int):
        """Mark recommendation as dismissed"""
        rec = self.get_by_id(recommendation_id)
        if rec:
            rec.is_dismissed = True
            self.db.commit()
            return rec
        return None


class HealthCheckLogRepository(BaseRepository[HealthCheckLog]):
    def __init__(self, db: Session):
        super().__init__(HealthCheckLog, db)

    def get_recent_scans(self, limit: int = 10):
        """Get recent health check scans"""
        return self.db.query(HealthCheckLog).order_by(
            HealthCheckLog.scan_timestamp.desc()
        ).limit(limit).all()

    def get_scan_trend(self, hours: int = 24):
        """Get health check trend over past N hours"""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return self.db.query(HealthCheckLog).filter(
            HealthCheckLog.scan_timestamp >= cutoff
        ).order_by(HealthCheckLog.scan_timestamp).all()
