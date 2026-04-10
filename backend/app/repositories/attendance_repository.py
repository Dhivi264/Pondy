from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from app.models.attendance import AttendanceSession, CameraPresenceSummary
from app.models.tracking import PersonSighting
from app.repositories.base_repository import BaseRepository


class AttendanceRepository(BaseRepository[AttendanceSession]):
    def __init__(self, db: Session):
        super().__init__(AttendanceSession, db)

    def get_sessions_by_date(self, attendance_date: date) -> List[AttendanceSession]:
        return (
            self.db.query(AttendanceSession)
            .filter(AttendanceSession.attendance_date == attendance_date)
            .all()
        )

    def _resolve_emp_id(self, emp_id) -> Optional[int]:
        if isinstance(emp_id, int):
            return emp_id
        if isinstance(emp_id, str) and emp_id.isdigit():
            return int(emp_id)
        from app.models.employee import Employee

        e = (
            self.db.query(Employee)
            .filter(Employee.employee_code == str(emp_id))
            .first()
        )
        return e.id if e else None

    def mark_attendance(self, employee_id):
        """Log presence for today. If already present, update exit_time."""
        emp_id_num = self._resolve_emp_id(employee_id)
        if not emp_id_num:
            return

        today = datetime.now().date()
        now = datetime.now()

        session = self.get_employee_daily_session(emp_id_num, today)
        if not session:
            session = AttendanceSession(
                employee_id=emp_id_num,
                attendance_date=today,
                entry_time=now,
                attendance_status="present",
            )
            self.db.add(session)
        else:
            session.exit_time = now

        self.db.commit()

    def log_tracking_event(self, employee_id, camera_id, zone: str = "Main"):
        """Record a sighting in the CameraPresenceSummary for the employee trail."""
        emp_id_num = self._resolve_emp_id(employee_id)
        if not emp_id_num:
            return

        cam_id_num = (
            int(camera_id)
            if isinstance(camera_id, str) and camera_id.isdigit()
            else (camera_id if isinstance(camera_id, int) else 1)
        )

        today = datetime.now().date()
        now = datetime.now()

        # Update daily camera summary
        summary = (
            self.db.query(CameraPresenceSummary)
            .filter(
                CameraPresenceSummary.employee_id == emp_id_num,
                CameraPresenceSummary.camera_id == cam_id_num,
                CameraPresenceSummary.attendance_date == today,
            )
            .first()
        )

        if not summary:
            summary = CameraPresenceSummary(
                employee_id=emp_id_num,
                camera_id=cam_id_num,
                attendance_date=today,
                first_seen=now,
                last_seen=now,
                sightings_count=1,
                total_visible_seconds=10,  # approximate ping duration
            )
            self.db.add(summary)
        else:
            summary.last_seen = now
            summary.sightings_count += 1
            if summary.first_seen:
                # Approximate duration update
                summary.total_visible_seconds = int(
                    (now - summary.first_seen).total_seconds()
                )

        # Create an individual raw sighting record
        sighting = PersonSighting(
            employee_id=emp_id_num,
            camera_id=cam_id_num,
            track_id=0,  # Generic track ID since we're bridging event systems
            first_seen=now,
            last_seen=now,
            duration_seconds=5,
            confidence_score=0.9,
        )
        self.db.add(sighting)

        self.db.commit()

    def create_sighting(self, sighting: PersonSighting) -> PersonSighting:
        self.db.add(sighting)
        self.db.commit()
        self.db.refresh(sighting)
        return sighting
