"""
LMP-TX Longitudinal Analysis Engine
=====================================
Builds per-employee temporal profiles across configurable time windows.
Derives behavioral metrics and risk flags.

All computation is pure Python/numpy — no external AI service needed.
The design is intentionally adapter-friendly: swap `_load_rows()` with
a real DB query once the schema is stable.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, date
from typing import List
import numpy as np

from app.lmp_tx.schemas import (
    AttendanceDaySnapshot,
    BehavioralMetrics,
    LongitudinalProfile,
    AnomalyEvent,
    AnomalyType,
    FusionEvent,
    ModalitySignal,
    Modality,
    LMPTXDashboardSummary,
)


# ─────────────────────────────────────────────────────────────────
# Synthetic data generator
# (replaces a real DB query in production)
# ─────────────────────────────────────────────────────────────────


def _synthetic_snapshots(
    employee_id: str,
    window_days: int,
    seed: int,
) -> List[AttendanceDaySnapshot]:
    """
    Generate realistic synthetic attendance snapshots for one employee
    over `window_days` working days.
    """
    rng = np.random.default_rng(seed)
    snapshots: List[AttendanceDaySnapshot] = []
    today = date.today()

    # Personality: punctual employee vs at-risk employee (seed-dependent)
    is_at_risk = seed % 4 == 0
    base_conf = 0.65 if is_at_risk else 0.88

    for offset in range(window_days - 1, -1, -1):
        d = today - timedelta(days=offset)
        if d.weekday() >= 5:  # skip weekends
            continue

        absent_p = 0.25 if is_at_risk else 0.06
        late_p = 0.35 if is_at_risk else 0.12

        r = rng.random()
        if r < absent_p:
            snapshots.append(
                AttendanceDaySnapshot(
                    date=d.isoformat(),
                    status="absent",
                    check_in_time=None,
                    check_out_time=None,
                    duration_hours=None,
                    confidence_score=None,
                    camera_sources=[],
                )
            )
            continue

        is_late = rng.random() < late_p
        hour_in = 9 if is_late else 8
        minute_in = int(rng.integers(0, 60))
        ci = datetime(d.year, d.month, d.day, hour_in, minute_in)
        dur = 7.5 + rng.normal(0, 0.5)
        dur = max(4.0, min(12.0, dur))
        co = ci + timedelta(hours=dur)
        conf = float(np.clip(base_conf + rng.normal(0, 0.05), 0.3, 1.0))

        cams = [f"cam_{rng.integers(1, 8)}", f"cam_{rng.integers(1, 4)}"]

        snapshots.append(
            AttendanceDaySnapshot(
                date=d.isoformat(),
                status="late" if is_late else "present",
                check_in_time=ci.strftime("%H:%M"),
                check_out_time=co.strftime("%H:%M"),
                duration_hours=round(dur, 2),
                confidence_score=round(conf, 4),
                camera_sources=list(set(cams)),
            )
        )

    return snapshots


# ─────────────────────────────────────────────────────────────────
# Metrics computation
# ─────────────────────────────────────────────────────────────────


def _compute_metrics(snapshots: List[AttendanceDaySnapshot]) -> BehavioralMetrics:
    working = len(snapshots)
    if working == 0:
        return BehavioralMetrics(
            avg_confidence_score=0,
            punctuality_rate=0,
            presence_rate=0,
            avg_daily_hours=0,
            consistency_score=0,
            trend_direction="stable",
        )

    absent = sum(1 for s in snapshots if s.status == "absent")
    present = working - absent
    late = sum(1 for s in snapshots if s.status == "late")
    on_time = present - late

    conf_vals = [
        s.confidence_score for s in snapshots if s.confidence_score is not None
    ]
    dur_vals = [s.duration_hours for s in snapshots if s.duration_hours is not None]

    avg_conf = float(np.mean(conf_vals)) if conf_vals else 0.0
    avg_dur = float(np.mean(dur_vals)) if dur_vals else 0.0
    presence_r = present / working if working else 0.0
    punct_r = on_time / present if present else 0.0

    # Consistency: inverse CV of confidence scores (low spread = consistent)
    if len(conf_vals) > 1:
        cv = float(np.std(conf_vals) / (avg_conf + 1e-9))
        consistency = float(np.clip(1.0 - cv, 0.0, 1.0))
    else:
        consistency = 1.0 if conf_vals else 0.0

    # Trend: compare first-half vs second-half presence rate
    mid = len(snapshots) // 2
    first_half = snapshots[:mid]
    second_half = snapshots[mid:]

    def _presence(chunk: List[AttendanceDaySnapshot]) -> float:
        if not chunk:
            return 0.0
        return sum(1 for s in chunk if s.status != "absent") / len(chunk)

    delta = _presence(second_half) - _presence(first_half)
    trend = (
        "improving" if delta > 0.05 else ("declining" if delta < -0.05 else "stable")
    )

    return BehavioralMetrics(
        avg_confidence_score=round(avg_conf, 4),
        punctuality_rate=round(punct_r, 4),
        presence_rate=round(presence_r, 4),
        avg_daily_hours=round(avg_dur, 2),
        consistency_score=round(consistency, 4),
        trend_direction=trend,
    )


def _compute_risk_flags(
    metrics: BehavioralMetrics,
    snapshots: List[AttendanceDaySnapshot],
) -> List[str]:
    flags: List[str] = []
    if metrics.avg_confidence_score < 0.70:
        flags.append("confidence_drop")
    if metrics.presence_rate < 0.75:
        flags.append("long_absence")
    if metrics.punctuality_rate < 0.60:
        flags.append("chronic_lateness")
    if metrics.trend_direction == "declining":
        flags.append("declining_trend")
    # Check for consecutive absences (≥3 days)
    streak = 0
    for s in reversed(snapshots):
        if s.status == "absent":
            streak += 1
        else:
            break
    if streak >= 3:
        flags.append("consecutive_absences")
    return flags


# ─────────────────────────────────────────────────────────────────
# Public engine class
# ─────────────────────────────────────────────────────────────────


class LongitudinalEngine:
    """
    Produces LongitudinalProfile objects for individual employees.
    In production: inject real DB rows instead of synthetic generation.
    """

    def build_profile(
        self,
        employee_id: str,
        employee_name: str,
        department: str,
        window_days: int = 30,
    ) -> LongitudinalProfile:
        seed = abs(hash(employee_id)) % 9999

        snapshots = _synthetic_snapshots(employee_id, window_days, seed)
        metrics = _compute_metrics(snapshots)
        flags = _compute_risk_flags(metrics, snapshots)

        today = date.today()
        return LongitudinalProfile(
            employee_id=employee_id,
            employee_name=employee_name,
            department=department,
            window_start=(today - timedelta(days=window_days)).isoformat(),
            window_end=today.isoformat(),
            total_days=len(snapshots),
            snapshots=snapshots,
            behavioral_metrics=metrics,
            risk_flags=flags,
        )


# ─────────────────────────────────────────────────────────────────
# Fusion Event Generator
# ─────────────────────────────────────────────────────────────────


class MultiModalFusionEngine:
    """
    Combines signals from multiple modalities (video, face, attendance)
    into a single fused event with a unified confidence score.

    Fusion rule: weighted average, with face recognition weighted highest.
    """

    WEIGHTS: dict = {
        Modality.FACE: 0.55,
        Modality.VIDEO: 0.25,
        Modality.ATTENDANCE: 0.20,
    }

    def fuse(self, signals: List[ModalitySignal]) -> FusionEvent:
        total_weight, weighted_sum = 0.0, 0.0
        for sig in signals:
            w = self.WEIGHTS.get(sig.modality, 0.1)
            weighted_sum += sig.raw_score * w
            total_weight += w

        fusion_score = weighted_sum / (total_weight or 1.0)

        if fusion_score >= 0.80:
            decision = "identity_confirmed"
        elif fusion_score >= 0.55:
            decision = "uncertain"
        else:
            decision = "anomaly"

        # Determine employee (from face signal)
        face_sig = next((s for s in signals if s.modality == Modality.FACE), None)
        zone = next(
            (s.metadata.get("zone") for s in signals if "zone" in s.metadata), None
        )

        return FusionEvent(
            event_id=uuid.uuid4().hex[:10],
            employee_id=face_sig.source_id
            if face_sig and fusion_score > 0.55
            else None,
            fusion_score=round(fusion_score, 4),
            modalities=signals,
            decision=decision,
            triggered_at=signals[0].timestamp if signals else datetime.now(),
            location_zone=zone,
        )


# ─────────────────────────────────────────────────────────────────
# Anomaly Detection Engine
# ─────────────────────────────────────────────────────────────────


class AnomalyDetectionEngine:
    """
    Rule-based + statistical anomaly detection on attendance + camera data.
    Designed to be augmented with ML models later.
    """

    def detect(
        self,
        employees: List[dict],
        attendance_rows: List[dict],
        camera_events: List[dict],
    ) -> List[AnomalyEvent]:
        events: List[AnomalyEvent] = []
        now = datetime.now()

        # Rule 1: confidence drop below threshold
        for row in attendance_rows:
            conf = row.get("confidence_score", 1.0)
            if conf is not None and conf < 0.65:
                events.append(
                    AnomalyEvent(
                        event_id=uuid.uuid4().hex[:10],
                        anomaly_type=AnomalyType.CONFIDENCE_DROP,
                        severity="medium",
                        employee_id=row.get("employee_id"),
                        camera_id=row.get("camera_source"),
                        detected_at=now,
                        description=(
                            f"Face recognition confidence {conf:.2%} is below "
                            f"the 65% threshold for employee {row.get('employee_id')}"
                        ),
                        evidence={"confidence": str(conf)},
                    )
                )

        # Rule 2: off-hours access (check-in before 6am or after 10pm)
        for row in attendance_rows:
            ci = row.get("check_in_time")
            if isinstance(ci, datetime) and (ci.hour < 6 or ci.hour >= 22):
                events.append(
                    AnomalyEvent(
                        event_id=uuid.uuid4().hex[:10],
                        anomaly_type=AnomalyType.OFF_HOURS_ACCESS,
                        severity="high",
                        employee_id=row.get("employee_id"),
                        camera_id=row.get("camera_source"),
                        detected_at=now,
                        description=(
                            f"Off-hours check-in at {ci.strftime('%H:%M')} "
                            f"for {row.get('employee_id')}"
                        ),
                        evidence={"check_in": str(ci)},
                    )
                )

        # Rule 3: attendance spike — more than 20% above baseline
        if attendance_rows:
            present_count = sum(
                1 for r in attendance_rows if r.get("status") in ("present", "late")
            )
            baseline = len(employees) * 0.7
            if present_count > baseline * 1.20:
                events.append(
                    AnomalyEvent(
                        event_id=uuid.uuid4().hex[:10],
                        anomaly_type=AnomalyType.ATTENDANCE_SPIKE,
                        severity="low",
                        employee_id=None,
                        camera_id=None,
                        detected_at=now,
                        description=(
                            f"Attendance spike: {present_count} present vs "
                            f"baseline ~{int(baseline)}"
                        ),
                        evidence={
                            "present": str(present_count),
                            "baseline": str(int(baseline)),
                        },
                    )
                )

        return events


# ─────────────────────────────────────────────────────────────────
# Enriched Dashboard Summary builder
# ─────────────────────────────────────────────────────────────────


def build_lmptx_summary(
    base: dict,
    anomaly_events: List[AnomalyEvent],
    fusion_events: List[FusionEvent],
    pending_al: int,
    profiles: List[LongitudinalProfile],
) -> LMPTXDashboardSummary:
    critical = sum(1 for a in anomaly_events if a.severity == "critical")
    at_risk = sum(
        1 for p in profiles if p.behavioral_metrics.trend_direction == "declining"
    )
    avg_conf = (
        float(np.mean([p.behavioral_metrics.avg_confidence_score for p in profiles]))
        if profiles
        else 0.0
    )

    return LMPTXDashboardSummary(
        **base,
        fusion_events_today=len(fusion_events),
        anomalies_today=len(anomaly_events),
        critical_anomalies=critical,
        pending_al_samples=pending_al,
        avg_face_confidence=round(avg_conf, 4),
        employees_at_risk=at_risk,
        longitudinal_coverage_days=30,
    )
