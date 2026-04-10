from datetime import date
from sqlalchemy.orm import Session
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.camera_repository import CameraRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.base_repository import BaseRepository
from app.models.archive import ArchiveRecord

class DashboardService:
    """
    Aggregates statistics for the Flutter frontend dashboard.
    """

    def __init__(self, db: Session):
        self._db = db
        self.att_repo = AttendanceRepository(db)
        self.cam_repo = CameraRepository(db)
        self.emp_repo = EmployeeRepository(db)
        self.arc_repo = BaseRepository(ArchiveRecord, db)

    def get_summary(self):
        """Fetch high-level overview statistics."""
        today = date.today()

        total_cameras = len(self.cam_repo.get_all())
        active_cameras = len(self.cam_repo.get_online_cameras())
        total_employees = len(self.emp_repo.get_all())

        # Today's attendance quick stats
        today_sessions = self.att_repo.get_sessions_by_date(today)
        present_count = len(
            [s for s in today_sessions if s.attendance_status == "present"]
        )

        total_archives = len(self.arc_repo.get_all(limit=10000))

        # Count actual anomalies
        from app.models.archive import ArchiveRecord
        anomalies_count = self._db.query(ArchiveRecord).filter(ArchiveRecord.event_type != "manual").count()

        # --- AI Performance Metrics ---
        from app.workers.stream_worker import stream_worker
        telemetry = stream_worker.telemetry
        lats = list(telemetry["latency_ms"].values())
        fpss = list(telemetry["fps_real"].values())
        
        avg_lat = sum(lats) / len(lats) if lats else 0.0
        avg_fps = sum(fpss) / len(fpss) if fpss else 0.0
        # ------------------------------

        return {
            "total_cameras": total_cameras,
            "active_cameras": active_cameras,
            "offline_cameras": total_cameras - active_cameras,
            "employees": total_employees,
            "present_today": present_count,
            "absent_today": total_employees - present_count,
            "archive_items": total_archives,
            "anomalies": anomalies_count,
            "al_samples": 0,
            "avg_ai_latency_ms": avg_lat,
            "global_ai_fps": avg_fps,
        }
