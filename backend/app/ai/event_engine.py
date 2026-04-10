import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TrackSession:
    track_id: int
    camera_id: int
    first_seen: datetime
    last_seen: datetime
    employee_id: Optional[int] = None
    confidence_sum: float = 0.0
    match_count: int = 0
    is_processed: bool = False
    is_loitering: bool = False  # Track if this session was flagged as loitering


class EventEngine:
    """
    Orchestrates tracking and face identification.
    Aggregates raw tracks into 'Sighting' events and 'Entry/Exit' events.
    """

    def __init__(self):
        # track_id -> session
        self.active_tracks: Dict[int, TrackSession] = {}
        self.timeout = timedelta(seconds=30)
        from app.config import settings
        self.loitering_threshold = settings.LOITERING_THRESHOLD_SECONDS

    def process_raw_track(
        self,
        camera_id: int,
        track_id: int,
        employee_id: Optional[int],
        confidence: float,
    ):
        """Update tracker state with new sightings."""
        now = datetime.now()

        if track_id in self.active_tracks:
            session = self.active_tracks[track_id]
            session.last_seen = now
            if employee_id:
                session.employee_id = employee_id
                session.confidence_sum += confidence
                session.match_count += 1
            
            # Check for loitering anomaly
            duration = (now - session.first_seen).total_seconds()
            if duration > self.loitering_threshold and not session.is_loitering:
                session.is_loitering = True
                logger.warning(f"⚠️ ANOMALY: Loitering detected for Track ID {track_id} on Camera {camera_id} (Duration: {duration:.1f}s)")
        else:
            self.active_tracks[track_id] = TrackSession(
                track_id=track_id,
                camera_id=camera_id,
                first_seen=now,
                last_seen=now,
                employee_id=employee_id,
                confidence_sum=confidence if employee_id else 0.0,
                match_count=1 if employee_id else 0,
            )

    def get_completed_events(self) -> List[TrackSession]:
        """Return and remove tracks that have timed out."""
        now = datetime.now()
        completed = []
        to_remove = []

        for tid, sess in self.active_tracks.items():
            if now - sess.last_seen > self.timeout:
                completed.append(sess)
                to_remove.append(tid)

        for tid in to_remove:
            del self.active_tracks[tid]

        return completed

    def determine_event_type(
        self, session: TrackSession, is_entry_cam: bool, is_exit_cam: bool
    ) -> str:
        """Heuristic for entry/exit determination."""
        if session.is_loitering:
            return "loitering_anomaly"

        if not session.employee_id:
            return "unknown_sighting"

        if is_entry_cam and not is_exit_cam:
            return "entry_candidate"
        if is_exit_cam and not is_entry_cam:
            return "exit_candidate"

        return "internal_sighting"
