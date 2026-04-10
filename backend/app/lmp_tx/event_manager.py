"""
LMP-TX Event Manager
====================
Coordinates the identification and tracking of employees across camera streams.
Triggers database updates (Attendance, Tracking) and video recording.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set
from dataclasses import dataclass, field

from app.repositories.attendance_repository import AttendanceRepository
from app.lmp_tx.face_recognizer import FaceRecognizer, FaceMatch

logger = logging.getLogger(__name__)


@dataclass
class ActiveSession:
    employee_id: str
    first_seen: datetime
    last_seen: datetime
    cameras_spotted: Set[str] = field(default_factory=set)
    confidence_buffer: List[float] = field(default_factory=list)
    is_active: bool = True


class EventManager:
    """
    Manages the lifecycle of an employee's presence in the facility.
    """

    def __init__(self, attendance_repo: AttendanceRepository):
        self.attendance_repo = attendance_repo
        self.face_recognizer = FaceRecognizer.get_instance()
        self.active_sessions: Dict[str, ActiveSession] = {}
        self.session_timeout = timedelta(minutes=5)

    def process_detections(self, camera_id: str, frame_np, detections: List[dict]):
        """
        Process a list of person detections from a camera frame.
        """
        # 1. Clean up stale sessions
        self._cleanup_sessions()

        for det in detections:
            # We only care about people for attendance (YOLO class 0)
            if det.get("class_id") != 0:
                continue

            # Crop and identify the face
            box = det.get(
                "box"
            )  # (x1, y1, x2, y2) -> face_recognizer uses (y1, x1, y2, x2)
            # Reformat box for FaceRecognizer
            fr_box = (box[1], box[0], box[3], box[2]) if box else None

            match: FaceMatch = self.face_recognizer.identify(frame_np, box=fr_box)

            if match.is_match:
                self._handle_match(camera_id, match)

    def _handle_match(self, camera_id: str, match: FaceMatch):
        """Handle a successful face match."""
        emp_id = match.employee_id
        now = datetime.now()

        if emp_id in self.active_sessions:
            # Update existing session
            session = self.active_sessions[emp_id]
            session.last_seen = now
            session.cameras_spotted.add(camera_id)
            session.confidence_buffer.append(match.confidence)

            # Periodic health check / log update
            if len(session.confidence_buffer) > 10:
                self.attendance_repo.log_tracking_event(emp_id, camera_id, zone="Main")
                session.confidence_buffer = []  # Clear buffer

            # Update check-out time in DB for every sighting (last sighting of the day is final)
            self.attendance_repo.mark_attendance(emp_id)
        else:
            # Create new session (Check-in)
            logger.info(
                f"[Events] New session started for employee: {emp_id} at {camera_id}"
            )
            self.active_sessions[emp_id] = ActiveSession(
                employee_id=emp_id,
                first_seen=now,
                last_seen=now,
                cameras_spotted={camera_id},
            )
            # Log check-in to database
            self.attendance_repo.mark_attendance(emp_id)
            self.attendance_repo.log_tracking_event(emp_id, camera_id, zone="Entrance")

    def _cleanup_sessions(self):
        """End sessions that haven't been seen for a while."""
        now = datetime.now()
        to_delete = []
        for emp_id, session in self.active_sessions.items():
            if now - session.last_seen > self.session_timeout:
                logger.info(
                    f"[Events] Session ended for employee: {emp_id}. Spotted by {len(session.cameras_spotted)} cameras."
                )
                to_delete.append(emp_id)
                # Final log update
                self.attendance_repo.mark_attendance(emp_id)

        for emp_id in to_delete:
            del self.active_sessions[emp_id]

    def get_active_count(self) -> int:
        return len(self.active_sessions)
