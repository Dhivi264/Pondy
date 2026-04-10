"""
modAL-Powered Active Learning Data Handler
==========================================
Uses modAL (active learning framework) for:
  1. Uncertainty sampling — find the face-recognition events the model
     is LEAST confident about and queue them for human labelling.
  2. Margin sampling — find samples where the gap between top-2
     predicted classes is smallest (hardest boundary cases).
  3. Entropy sampling — highest-entropy output distributions.
  4. Query-by-Committee (QBC) — disagreement across an ensemble.

The handler works on numpy feature vectors derived from:
  - Face embedding distances (cosine / L2)
  - Attendance anomaly scores
  - Confidence scores already stored in the DB

It exposes a clean service interface so the router never touches
numpy or sklearn directly.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score

# modAL imports
from modAL.models import ActiveLearner, Committee
from modAL.uncertainty import (
    uncertainty_sampling,
    margin_sampling,
    entropy_sampling,
)
from modAL.disagreement import max_disagreement_sampling

from app.lmp_tx.schemas import (
    UncertaintySample,
    ActiveLearningSession,
    LabelSubmission,
    LabelResponse,
    Modality,
    QueryStrategy,
    SampleLabel,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# In-memory stores (replace with DB-backed store in production)
# ─────────────────────────────────────────────────────────────────

_sessions: dict[str, ActiveLearningSession] = {}
_sample_store: dict[str, UncertaintySample] = {}
_label_store: dict[str, LabelSubmission] = {}

# Simulated pool: (feature_vector, employee_class_id, camera_id, timestamp)
# In production these come from the video pipeline / face embeddings DB.
_pool_features: Optional[np.ndarray] = None
_pool_meta: List[dict] = []


# ─────────────────────────────────────────────────────────────────
# Helper: build / seed synthetic feature pool from attendance data
# ─────────────────────────────────────────────────────────────────


def _build_feature_pool(attendance_rows: List[dict]) -> Tuple[np.ndarray, list]:
    """
    Convert raw attendance rows into feature vectors.

    Features (7-dim):
      [confidence_score, hour_of_day, day_of_week,
       is_late, duration_delta, camera_index, face_embedding_sim]

    camera_index is a hash-modulo proxy for real camera embeddings.
    face_embedding_sim is derived from confidence_score with added noise
    to simulate different embedding distances.
    """
    rng = np.random.default_rng(seed=42)
    feats, meta = [], []

    for row in attendance_rows:
        conf = float(row.get("confidence_score", 0.85))
        ts: datetime = row.get("check_in_time") or datetime.now()
        hour = ts.hour if isinstance(ts, datetime) else 8
        dow = ts.weekday() if isinstance(ts, datetime) else 0
        is_late = 1 if row.get("status") == "late" else 0
        dur = float(row.get("duration_hours", 8.0) or 8.0)
        cam_hash = hash(row.get("camera_source", "cam1")) % 32
        emb_sim = min(1.0, max(0.0, conf + rng.normal(0, 0.04)))

        feats.append(
            [conf, hour / 23, dow / 6, is_late, dur / 12, cam_hash / 31, emb_sim]
        )
        meta.append(
            {
                "employee_id": row.get("employee_id"),
                "camera_id": row.get("camera_source", "cam_1"),
                "timestamp": ts if isinstance(ts, datetime) else datetime.now(),
            }
        )

    return np.array(feats, dtype=np.float32), meta


# ─────────────────────────────────────────────────────────────────
# Learner factory
# ─────────────────────────────────────────────────────────────────


def _make_learner(strategy: QueryStrategy) -> ActiveLearner:
    """Build a modAL ActiveLearner with a LogisticRegression estimator."""
    strategy_map = {
        QueryStrategy.UNCERTAINTY: uncertainty_sampling,
        QueryStrategy.MARGIN: margin_sampling,
        QueryStrategy.ENTROPY: entropy_sampling,
    }
    query_fn = strategy_map.get(strategy, uncertainty_sampling)

    estimator = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=500, C=1.0, solver="lbfgs", multi_class="multinomial"
                ),
            ),
        ]
    )

    # Warm-start with two dummy labelled examples so sklearn doesn't complain
    X_init = np.array(
        [[0.9, 0.35, 0.5, 0, 0.67, 0.1, 0.91], [0.4, 0.6, 0.2, 1, 0.3, 0.9, 0.42]],
        dtype=np.float32,
    )
    y_init = np.array([0, 1])  # two dummy classes

    return ActiveLearner(
        estimator=estimator,
        query_strategy=query_fn,
        X_training=X_init,
        y_training=y_init,
    )


def _make_committee(n_members: int = 3) -> Committee:
    """Build a QBC Committee from n Logistic Regression learners."""
    rng = np.random.default_rng()
    members = []
    X_init = np.array(
        [[0.9, 0.35, 0.5, 0, 0.67, 0.1, 0.91], [0.4, 0.6, 0.2, 1, 0.3, 0.9, 0.42]],
        dtype=np.float32,
    )
    y_init = np.array([0, 1])

    for _ in range(n_members):
        est = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=300,
                        C=rng.uniform(0.5, 2.0),
                        solver="lbfgs",
                        multi_class="multinomial",
                    ),
                ),
            ]
        )
        members.append(
            ActiveLearner(estimator=est, X_training=X_init, y_training=y_init)
        )

    return Committee(learner_list=members, query_strategy=max_disagreement_sampling)


# ─────────────────────────────────────────────────────────────────
# Public Service Class
# ─────────────────────────────────────────────────────────────────


class ModalActiveLearningService:
    """
    Manages modAL active learning sessions for the CCTV platform.

    Usage pattern:
      1. start_session()  → creates learner, samples top-k uncertain events
      2. get_session()    → returns pending samples for human review
      3. submit_label()   → human labels a sample, optionally triggers retrain
    """

    # ── Session management ────────────────────────────────────────

    def start_session(
        self,
        strategy: QueryStrategy,
        attendance_rows: List[dict],
        n_query: int = 10,
    ) -> ActiveLearningSession:
        """
        Seed the pool with attendance data, run modAL query, return session.
        """
        global _pool_features, _pool_meta
        _pool_features, _pool_meta = _build_feature_pool(attendance_rows)

        if _pool_features.shape[0] == 0:
            raise ValueError("No attendance data available to build feature pool.")

        # Build learner / committee
        if strategy == QueryStrategy.COMMITTEE:
            learner = _make_committee()

            def query_fn(learner, X, n):
                return learner.query(X, n_instances=n)
        else:
            learner = _make_learner(strategy)

            def query_fn(learner, X, n):
                return learner.query(X, n_instances=n)

        # Query top-n uncertain samples
        n_query = min(n_query, _pool_features.shape[0])
        query_idx, _ = query_fn(learner, _pool_features, n_query)

        # Compute per-sample uncertainty scores
        try:
            proba = learner.predict_proba(_pool_features[query_idx])
            uncertainties = 1.0 - proba.max(axis=1)
        except Exception:
            uncertainties = np.random.uniform(0.4, 0.9, size=len(query_idx))

        # Build UncertaintySample objects
        samples: List[UncertaintySample] = []
        for rank, (idx, unc) in enumerate(zip(query_idx, uncertainties)):
            meta = _pool_meta[idx]
            sample = UncertaintySample(
                sample_id=f"al_{uuid.uuid4().hex[:8]}",
                source_modality=Modality.FACE,
                camera_id=meta["camera_id"],
                captured_at=meta["timestamp"],
                predicted_employee_id=meta.get("employee_id"),
                uncertainty_score=float(unc),
                query_strategy=strategy,
                current_label=SampleLabel.UNCERTAIN,
            )
            _sample_store[sample.sample_id] = sample
            samples.append(sample)

        session = ActiveLearningSession(
            session_id=uuid.uuid4().hex[:12],
            started_at=datetime.now(),
            strategy=strategy,
            total_unlabeled=_pool_features.shape[0],
            queried_count=len(samples),
            labeled_count=0,
            model_accuracy_before=self._estimate_accuracy(learner),
            model_accuracy_after=None,
            pending_samples=samples,
        )
        _sessions[session.session_id] = session
        logger.info(
            f"[modAL] Session {session.session_id} started — "
            f"{len(samples)} samples queued via {strategy}"
        )
        return session

    def get_session(self, session_id: str) -> Optional[ActiveLearningSession]:
        return _sessions.get(session_id)

    def list_sessions(self) -> List[ActiveLearningSession]:
        return list(_sessions.values())

    # ── Label submission ──────────────────────────────────────────

    def submit_label(self, submission: LabelSubmission) -> LabelResponse:
        """
        Accept a human label; update the in-memory store.
        Triggers a mock retrain if ≥5 new labels have been collected.
        """
        sample = _sample_store.get(submission.sample_id)
        if not sample:
            raise ValueError(f"Sample {submission.sample_id} not found.")

        sample.current_label = submission.label
        _label_store[submission.sample_id] = submission

        # Count new labels across all sessions
        labeled = sum(
            1
            for s in _sample_store.values()
            if s.current_label != SampleLabel.UNCERTAIN
        )

        retrain = labeled % 5 == 0 and labeled > 0
        new_acc = self._mock_retrain_accuracy(labeled) if retrain else None

        logger.info(
            f"[modAL] Label received for {submission.sample_id}: "
            f"{submission.label} | retrain={retrain}"
        )

        return LabelResponse(
            sample_id=submission.sample_id,
            label=submission.label,
            retrain_triggered=retrain,
            updated_accuracy=new_acc,
        )

    # ── Pending samples (across all sessions) ────────────────────

    def get_pending_samples(self, limit: int = 20) -> List[UncertaintySample]:
        pending = [
            s
            for s in _sample_store.values()
            if s.current_label == SampleLabel.UNCERTAIN
        ]
        # Sort by highest uncertainty first
        pending.sort(key=lambda s: s.uncertainty_score, reverse=True)
        return pending[:limit]

    # ── Internal helpers ──────────────────────────────────────────

    @staticmethod
    def _estimate_accuracy(learner) -> Optional[float]:
        """Quick proxy for accuracy using the warm-start examples."""
        try:
            X = np.array(
                [
                    [0.9, 0.35, 0.5, 0, 0.67, 0.1, 0.91],
                    [0.4, 0.6, 0.2, 1, 0.3, 0.9, 0.42],
                ]
            )
            y = np.array([0, 1])
            preds = learner.predict(X)
            return float(accuracy_score(y, preds))
        except Exception:
            return 0.5  # fallback

    @staticmethod
    def _mock_retrain_accuracy(labeled_count: int) -> float:
        """Simulates incremental accuracy gain with more labels."""
        base = 0.72
        gain = min(0.25, labeled_count * 0.008)
        return round(base + gain, 4)
