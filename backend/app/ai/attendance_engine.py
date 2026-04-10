import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.attendance import AttendanceSession

logger = logging.getLogger(__name__)


class AttendanceEngine:
    """
    Translates sighting events into daily attendance records.
    Handles check-in, check-out, and late detection.
    """

    def __init__(self, db: Session):
        self.db = db

    def process_event(
        self, employee_id: int, timestamp: datetime, camera_id: int, event_type: str
    ):
        """Update or create an attendance record for the employee."""
        try:
            today = timestamp.date()

            # Find existing session for today
            session = (
                self.db.query(AttendanceSession)
                .filter(
                    AttendanceSession.employee_id == employee_id,
                    AttendanceSession.attendance_date == today,
                )
                .one_or_none()
            )

            if not session:
                # Create new session (Check-In)
                session = AttendanceSession(
                    employee_id=employee_id,
                    attendance_date=today,
                    entry_time=timestamp,
                    entry_camera_id=camera_id,
                    attendance_status="present",
                )
                self.db.add(session)
                logger.info(
                    f"[Attendance] Check-in for employee {employee_id} at {timestamp}"
                )
            else:
                # Update existing session (Check-Out)
                # In this logic, we update exit_time to the latest sighting time
                session.exit_time = timestamp
                session.exit_camera_id = camera_id

                # Record loitering event if triggered
                if event_type == "loitering_anomaly":
                    session.loitering_flag = 1
                    session.last_anomaly_detected = timestamp
                    session.total_suspicious_duration += 10 # Estimated time increment between AI checks

            self.db.commit()
            return session
        except Exception as e:
            logger.error(f"[Attendance] Error processing event: {e}")
            self.db.rollback()
            return None
