"""
LMP-TX: Longitudinal Multi-modal Platform — Schemas
Covers:
  - Longitudinal temporal profiles per employee
  - Multi-modal fusion events (video + face + attendance)
  - modAL active learning uncertainty samples
  - Anomaly detection events
  - Behavioral pattern summaries
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


# ─────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────


class Modality(str, Enum):
    VIDEO = "video"
    FACE = "face"
    ATTENDANCE = "attendance"
    AUDIO = "audio"  # future-proofed
    ACCESS = "access_control"  # door/badge future


class AnomalyType(str, Enum):
    UNKNOWN_FACE = "unknown_face"
    TAILGATING = "tailgating"
    ATTENDANCE_SPIKE = "attendance_spike"
    LONG_ABSENCE = "long_absence"
    OFF_HOURS_ACCESS = "off_hours_access"
    CONFIDENCE_DROP = "confidence_drop"


class QueryStrategy(str, Enum):
    UNCERTAINTY = "uncertainty_sampling"
    MARGIN = "margin_sampling"
    ENTROPY = "entropy_sampling"
    COMMITTEE = "query_by_committee"


class SampleLabel(str, Enum):
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"


# ─────────────────────────────────────────
# LONGITUDINAL PROFILE (per employee, over time)
# ─────────────────────────────────────────


class AttendanceDaySnapshot(BaseModel):
    """Single-day roll-up used inside a longitudinal profile."""

    date: str  # ISO date string YYYY-MM-DD
    status: str  # present / absent / late
    check_in_time: Optional[str]
    check_out_time: Optional[str]
    duration_hours: Optional[float]
    confidence_score: Optional[float]
    camera_sources: List[str] = []


class BehavioralMetrics(BaseModel):
    """Derived KPIs computed across the longitudinal window."""

    avg_confidence_score: float  # mean face-recog confidence
    punctuality_rate: float  # fraction of days on time
    presence_rate: float  # fraction of working days present
    avg_daily_hours: float
    consistency_score: float = Field(
        ..., description="0-1: how consistent the pattern is across the window"
    )
    trend_direction: str = Field(..., description="improving / stable / declining")


class LongitudinalProfile(BaseModel):
    """Full longitudinal profile for one employee over a time window."""

    employee_id: str
    employee_name: str
    department: str
    window_start: str
    window_end: str
    total_days: int
    snapshots: List[AttendanceDaySnapshot]
    behavioral_metrics: BehavioralMetrics
    risk_flags: List[str] = []  # e.g. ["long_absence", "confidence_drop"]


# ─────────────────────────────────────────
# MULTI-MODAL FUSION EVENT
# ─────────────────────────────────────────


class ModalitySignal(BaseModel):
    """One modality's contribution to a fusion event."""

    modality: Modality
    source_id: str  # camera_id or "attendance_system"
    raw_score: float  # 0.0-1.0 confidence / activation
    timestamp: datetime
    metadata: Dict[str, str] = {}


class FusionEvent(BaseModel):
    """
    Multi-modal fusion event: combines signals from ≥2 modalities
    to produce a fused identity confirmation or anomaly signal.
    """

    event_id: str
    employee_id: Optional[str]  # None if identity unknown
    fusion_score: float  # 0-1 fused confidence
    modalities: List[ModalitySignal]
    decision: str  # "identity_confirmed" | "anomaly" | "uncertain"
    triggered_at: datetime
    location_zone: Optional[str]


# ─────────────────────────────────────────
# ANOMALY DETECTION
# ─────────────────────────────────────────


class AnomalyEvent(BaseModel):
    event_id: str
    anomaly_type: AnomalyType
    severity: str  # low / medium / high / critical
    employee_id: Optional[str]
    camera_id: Optional[str]
    detected_at: datetime
    description: str
    evidence: Dict[str, str] = {}  # supporting data points
    resolved: bool = False


# ─────────────────────────────────────────
# modAL ACTIVE LEARNING
# ─────────────────────────────────────────


class UncertaintySample(BaseModel):
    """
    A face / attendance record flagged by the active learner as uncertain —
    needs human annotation to improve the model.
    """

    sample_id: str
    source_modality: Modality
    camera_id: str
    captured_at: datetime
    predicted_employee_id: Optional[str]
    uncertainty_score: float  # 1.0 = maximally uncertain
    query_strategy: QueryStrategy
    current_label: SampleLabel = SampleLabel.UNCERTAIN
    frame_path: Optional[str] = None  # path/URL to the video frame


class ActiveLearningSession(BaseModel):
    """Snapshot of a running active learning session."""

    session_id: str
    started_at: datetime
    strategy: QueryStrategy
    total_unlabeled: int
    queried_count: int
    labeled_count: int
    model_accuracy_before: Optional[float]
    model_accuracy_after: Optional[float]
    pending_samples: List[UncertaintySample]


class LabelSubmission(BaseModel):
    """Human submits a label for a queried sample."""

    sample_id: str
    confirmed_employee_id: Optional[str]  # None if reject / unknown
    label: SampleLabel
    annotator_id: str


class LabelResponse(BaseModel):
    sample_id: str
    label: SampleLabel
    retrain_triggered: bool
    updated_accuracy: Optional[float]


# ─────────────────────────────────────────
# DASHBOARD SUMMARY (LMP-TX enriched)
# ─────────────────────────────────────────


class LMPTXDashboardSummary(BaseModel):
    """Drop-in replacement / extension for existing DashboardSummaryResponse."""

    # Base metrics (mirrored from existing)
    total_cameras: int
    active_cameras: int
    offline_cameras: int
    employees: int
    attendance_records: int
    archive_items: int

    # LMP-TX enrichments
    fusion_events_today: int
    anomalies_today: int
    critical_anomalies: int
    pending_al_samples: int  # modAL queue size
    avg_face_confidence: float
    employees_at_risk: int  # count with declining trend
    longitudinal_coverage_days: int  # how many days of history used
