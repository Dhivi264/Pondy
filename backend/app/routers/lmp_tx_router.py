"""
LMP-TX Router
=============
Exposes all Longitudinal Multi-modal Platform endpoints:

  GET  /lmp/profile/{employee_id}          — longitudinal profile
  GET  /lmp/profiles                       — batch profiles (all employees)
  GET  /lmp/anomalies                      — detected anomaly events
  GET  /lmp/fusion-events                  — multi-modal fusion log
  GET  /lmp/dashboard                      — enriched LMP-TX dashboard summary
  POST /lmp/al/start-session               — start a modAL active learning session
  GET  /lmp/al/sessions                    — list AL sessions
  GET  /lmp/al/sessions/{session_id}       — get specific session + pending samples
  GET  /lmp/al/pending-samples             — top uncertain samples needing labels
  POST /lmp/al/label                       — human submits a label
"""

from datetime import datetime
from typing import List, Optional
import pyodbc

from fastapi import APIRouter, Depends, Query, HTTPException

from app.access_db import get_db_connection
from app.deps import get_current_user
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.dashboard_repository import DashboardRepository

from app.lmp_tx.schemas import (
    LongitudinalProfile,
    AnomalyEvent,
    FusionEvent,
    ModalitySignal,
    Modality,
    LMPTXDashboardSummary,
    ActiveLearningSession,
    UncertaintySample,
    LabelSubmission,
    LabelResponse,
    QueryStrategy,
)
from app.lmp_tx.longitudinal_engine import (
    LongitudinalEngine,
    AnomalyDetectionEngine,
    MultiModalFusionEngine,
    build_lmptx_summary,
)
from app.lmp_tx.modal_handler import ModalActiveLearningService
from app.lmp_tx.rtsp_manager import RTSPStreamManager, StreamQuality as RTSPQuality
from app.lmp_tx.frame_processor import (
    YOLOModelLoader,
    AdaptiveFrameSkipController,
    HardwareProfile,
    HARDWARE_CONFIGS,
)
from app.lmp_tx.camera_schemas import (
    RTSPCameraCreate,
    RTSPCameraResponse,
    FrameSkipStatusResponse,
    HardwareProfileResponse,
)

router = APIRouter(
    prefix="/lmp",
    tags=["LMP-TX — AI Longitudinal Multi-modal Platform"],
    dependencies=[Depends(get_current_user)],
)

# Singletons (stateful services)
_longitudinal_engine = LongitudinalEngine()
_anomaly_engine = AnomalyDetectionEngine()
_fusion_engine = MultiModalFusionEngine()
_al_service = ModalActiveLearningService()
_rtsp_manager = RTSPStreamManager()
_frame_skip_ctrl = AdaptiveFrameSkipController(skip_rate=1, dynamic=True)
_yolo_loader = YOLOModelLoader.get_instance(HardwareProfile.AUTO)


# ─────────────────────────────────────────────────────────────────
# Helpers: load data from DB repositories
# ─────────────────────────────────────────────────────────────────


def _get_emp_repo(db: pyodbc.Connection = Depends(get_db_connection)):
    return EmployeeRepository(db)


def _get_att_repo(db: pyodbc.Connection = Depends(get_db_connection)):
    return AttendanceRepository(db)


def _employees_as_dicts(repo: EmployeeRepository) -> List[dict]:
    rows = repo.get_all()
    return [r.model_dump() for r in rows] if rows else []


def _attendance_as_dicts(repo: AttendanceRepository) -> List[dict]:
    rows = repo.get_all()
    return [r.model_dump() for r in rows] if rows else []


# ─────────────────────────────────────────────────────────────────
# Longitudinal Profiles
# ─────────────────────────────────────────────────────────────────


@router.get("/profile/{employee_id}", response_model=LongitudinalProfile)
def get_longitudinal_profile(
    employee_id: str,
    window_days: int = Query(30, ge=7, le=365),
    emp_repo: EmployeeRepository = Depends(_get_emp_repo),
):
    """
    Return a full longitudinal profile for one employee.
    Includes day-by-day attendance snapshots, behavioral KPIs,
    and AI-derived risk flags over the requested time window.
    """
    emp = emp_repo.get_by_id(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return _longitudinal_engine.build_profile(
        employee_id=emp.employee_id,
        employee_name=emp.name,
        department=emp.department,
        window_days=window_days,
    )


@router.get("/profiles", response_model=List[LongitudinalProfile])
def get_all_longitudinal_profiles(
    window_days: int = Query(30, ge=7, le=90),
    department: Optional[str] = None,
    risk_only: bool = False,
    emp_repo: EmployeeRepository = Depends(_get_emp_repo),
):
    """
    Batch longitudinal profiles.
    Filter by department or return only at-risk employees.
    """
    emps = emp_repo.get_all(search=department)
    profiles: List[LongitudinalProfile] = []
    for emp in emps:
        p = _longitudinal_engine.build_profile(
            employee_id=emp.employee_id,
            employee_name=emp.name,
            department=emp.department,
            window_days=window_days,
        )
        if risk_only and not p.risk_flags:
            continue
        profiles.append(p)
    return profiles


# ─────────────────────────────────────────────────────────────────
# Anomaly Detection
# ─────────────────────────────────────────────────────────────────


@router.get("/anomalies", response_model=List[AnomalyEvent])
def get_anomalies(
    severity: Optional[str] = None,
    emp_repo: EmployeeRepository = Depends(_get_emp_repo),
    att_repo: AttendanceRepository = Depends(_get_att_repo),
):
    """
    Run anomaly detection against current attendance + camera data.
    Optional severity filter: low | medium | high | critical.
    """
    employees = _employees_as_dicts(emp_repo)
    attendance = _attendance_as_dicts(att_repo)

    events = _anomaly_engine.detect(
        employees=employees,
        attendance_rows=attendance,
        camera_events=[],  # camera_events injected by video pipeline in production
    )

    if severity:
        events = [e for e in events if e.severity == severity]

    return events


# ─────────────────────────────────────────────────────────────────
# Multi-modal Fusion Events
# ─────────────────────────────────────────────────────────────────


@router.get("/fusion-events", response_model=List[FusionEvent])
def get_fusion_events(
    limit: int = Query(20, ge=1, le=100),
    att_repo: AttendanceRepository = Depends(_get_att_repo),
):
    """
    Return simulated multi-modal fusion events built from recent
    attendance records.  In production this is fed by the video pipeline.
    """
    rows = _attendance_as_dicts(att_repo)
    events: List[FusionEvent] = []

    for row in rows[:limit]:
        face_score = float(row.get("confidence_score") or 0.85)
        ts = row.get("check_in_time") or datetime.now()
        if not isinstance(ts, datetime):
            ts = datetime.now()

        signals = [
            ModalitySignal(
                modality=Modality.FACE,
                source_id=str(row.get("employee_id", "unknown")),
                raw_score=face_score,
                timestamp=ts,
                metadata={"zone": "entrance"},
            ),
            ModalitySignal(
                modality=Modality.ATTENDANCE,
                source_id="attendance_system",
                raw_score=0.95 if row.get("status") == "present" else 0.4,
                timestamp=ts,
                metadata={},
            ),
            ModalitySignal(
                modality=Modality.VIDEO,
                source_id="cam_1",
                raw_score=min(1.0, face_score + 0.05),
                timestamp=ts,
                metadata={"zone": "entrance"},
            ),
        ]
        events.append(_fusion_engine.fuse(signals))

    return events


# ─────────────────────────────────────────────────────────────────
# Enriched Dashboard
# ─────────────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=LMPTXDashboardSummary)
def get_lmptx_dashboard(
    emp_repo: EmployeeRepository = Depends(_get_emp_repo),
    att_repo: AttendanceRepository = Depends(_get_att_repo),
    db: pyodbc.Connection = Depends(get_db_connection),
):
    """
    Enriched dashboard summary that extends the base dashboard with
    LMP-TX AI metrics: fusion events, anomalies, modAL queue size,
    at-risk employee count, and average face confidence.
    """
    employees = _employees_as_dicts(emp_repo)
    attendance = _attendance_as_dicts(att_repo)

    dash_repo = DashboardRepository(db)
    dash_stats = dash_repo.get_summary()

    base = {
        "total_cameras": dash_stats.total_cameras,
        "active_cameras": dash_stats.active_cameras,
        "offline_cameras": dash_stats.offline_cameras,
        "employees": dash_stats.employees,
        "attendance_records": dash_stats.attendance_records,
        "archive_items": dash_stats.archive_items,
    }

    anomalies = _anomaly_engine.detect(employees, attendance, [])
    fusion_events = []  # lightweight: skip fusion recompute for dashboard

    profiles = [
        _longitudinal_engine.build_profile(
            employee_id=e.get("employee_id", ""),
            employee_name=e.get("name", ""),
            department=e.get("department", ""),
            window_days=30,
        )
        for e in employees[:20]  # cap at 20 for dashboard performance
    ]

    pending = len(_al_service.get_pending_samples(limit=200))

    return build_lmptx_summary(base, anomalies, fusion_events, pending, profiles)


# ─────────────────────────────────────────────────────────────────
# modAL Active Learning Endpoints
# ─────────────────────────────────────────────────────────────────


@router.post("/al/start-session", response_model=ActiveLearningSession)
def start_al_session(
    strategy: QueryStrategy = QueryStrategy.UNCERTAINTY,
    n_query: int = Query(10, ge=1, le=50),
    att_repo: AttendanceRepository = Depends(_get_att_repo),
):
    """
    Start a new modAL active learning session.
    Queries the n_query most uncertain attendance/face samples
    using the chosen strategy (uncertainty / margin / entropy / committee).
    """
    attendance = _attendance_as_dicts(att_repo)

    if not attendance:
        raise HTTPException(
            status_code=400,
            detail="No attendance records found to start an AL session. Please add employee data first.",
        )

    try:
        session = _al_service.start_session(
            strategy=strategy,
            attendance_rows=attendance,
            n_query=n_query,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return session


@router.get("/al/sessions", response_model=List[ActiveLearningSession])
def list_al_sessions():
    """List all active learning sessions with their status."""
    return _al_service.list_sessions()


@router.get("/al/sessions/{session_id}", response_model=ActiveLearningSession)
def get_al_session(session_id: str):
    """Get a specific AL session including its pending sample queue."""
    session = _al_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/al/pending-samples", response_model=List[UncertaintySample])
def get_pending_samples(limit: int = Query(20, ge=1, le=100)):
    """
    Return top uncertain samples (highest uncertainty score first)
    that are awaiting human annotation.
    Sorted by modAL uncertainty score descending.
    """
    return _al_service.get_pending_samples(limit=limit)


@router.post("/al/label", response_model=LabelResponse)
def submit_label(submission: LabelSubmission):
    """
    Submit a human annotation for a queried sample.
    When enough labels accumulate, a model retrain is triggered automatically.
    """
    try:
        return _al_service.submit_label(submission)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─────────────────────────────────────────────────────────────────
# RTSP Camera Registration & Management
# ─────────────────────────────────────────────────────────────────


@router.post("/cameras/register", response_model=RTSPCameraResponse)
def register_rtsp_camera(payload: RTSPCameraCreate):
    """
    Register an IP camera using its RTSP parameters.
    Builds the correct RTSP URL from the manufacturer template and
    probes the stream to confirm it is reachable.

    Supported manufacturers: hikvision, dahua, axis, hanwha, bosch,
    vivotek, uniview, reolink, amcrest, generic.

    Tip: Use ONVIF Device Manager to discover the exact URL format
    for your specific camera model if it is not listed here.
    """
    info = _rtsp_manager.build_url(
        camera_id=payload.camera_id,
        manufacturer=payload.manufacturer,
        user=payload.rtsp_user,
        password=payload.rtsp_password,
        ip=payload.ip_address,
        channel=payload.channel,
        quality=RTSPQuality(payload.quality.value),
    )
    is_alive, probe_msg = _rtsp_manager.probe(info)

    return RTSPCameraResponse(
        camera_id=info.camera_id,
        name=payload.name,
        manufacturer=payload.manufacturer,
        masked_url=info.masked_url,
        channel=payload.channel,
        quality=payload.quality,
        is_alive=is_alive,
        probe_message=probe_msg,
    )


@router.post("/cameras/register-raw", response_model=RTSPCameraResponse)
def register_raw_rtsp(camera_id: str, name: str, rtsp_url: str):
    """
    Register a camera using a manually supplied RTSP URL.
    Use this when you already know your camera's exact stream URL
    (e.g. from your camera manual or ONVIF Device Manager).
    """
    try:
        info = _rtsp_manager.register_raw(camera_id, rtsp_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    is_alive, probe_msg = _rtsp_manager.probe(info)
    return RTSPCameraResponse(
        camera_id=info.camera_id,
        name=name,
        manufacturer="manual",
        masked_url=info.masked_url,
        channel=1,
        quality=RTSPQuality.MAIN,
        is_alive=is_alive,
        probe_message=probe_msg,
    )


@router.get("/cameras/probe/{camera_id}", response_model=RTSPCameraResponse)
def probe_camera(camera_id: str):
    """Re-probe an already registered camera to check stream health."""
    info = _rtsp_manager.get(camera_id)
    if not info:
        raise HTTPException(
            status_code=404, detail="Camera not registered in RTSP manager"
        )
    is_alive, probe_msg = _rtsp_manager.probe(info)
    return RTSPCameraResponse(
        camera_id=info.camera_id,
        name=camera_id,
        manufacturer=info.manufacturer,
        masked_url=info.masked_url,
        channel=info.channel,
        quality=RTSPQuality(info.quality.value),
        is_alive=is_alive,
        probe_message=probe_msg,
    )


@router.get("/cameras/rtsp-templates")
def list_rtsp_templates():
    """
    Return the catalogue of supported manufacturer RTSP URL templates.
    Use these to manually construct URLs or verify ONVIF-discovered ones.
    """
    from app.lmp_tx.rtsp_manager import RTSP_TEMPLATES

    return {
        "manufacturers": list(RTSP_TEMPLATES.keys()),
        "templates": RTSP_TEMPLATES,
        "tip": (
            "If your manufacturer is not listed, use 'generic' or supply "
            "the raw URL via /lmp/cameras/register-raw. "
            "ONVIF Device Manager can auto-discover the correct URL."
        ),
    }


# ─────────────────────────────────────────────────────────────────
# Hardware Profile & Frame Skip
# ─────────────────────────────────────────────────────────────────


@router.get("/hardware/profile", response_model=HardwareProfileResponse)
def get_hardware_profile():
    """
    Detect the current server hardware and return the recommended
    YOLO model variant and frame skip configuration.

    On Raspberry Pi or Intel NCS2, the Nano model (YOLOv8n) is
    selected automatically with skip_rate=5 for smooth throughput.
    """
    cfg = _yolo_loader.config
    return HardwareProfileResponse(
        detected_profile=cfg.profile.value,
        yolo_variant=cfg.yolo_variant,
        yolo_backend=cfg.yolo_backend,
        default_skip_rate=cfg.default_skip,
        max_resolution_w=cfg.max_resolution[0],
        max_resolution_h=cfg.max_resolution[1],
        notes=cfg.notes,
    )


@router.get("/hardware/all-profiles")
def list_all_hardware_profiles():
    """
    Return the full matrix of hardware profiles with their YOLO model
    and frame skip recommendations.
    """
    return [
        {
            "profile": cfg.profile.value,
            "yolo_variant": cfg.yolo_variant,
            "yolo_backend": cfg.yolo_backend,
            "default_skip": cfg.default_skip,
            "max_resolution": f"{cfg.max_resolution[0]}x{cfg.max_resolution[1]}",
            "notes": cfg.notes,
        }
        for cfg in HARDWARE_CONFIGS.values()
    ]


@router.get("/cameras/frame-skip-stats", response_model=List[FrameSkipStatusResponse])
def get_frame_skip_stats():
    """
    Return real-time frame skip statistics for all active camera streams.
    Shows current skip rate, processed frame count, average inference time,
    and effective FPS per camera.
    """
    return [
        FrameSkipStatusResponse(
            camera_id=s.camera_id,
            current_skip_rate=s.current_skip_rate,
            total_frames_received=s.total_frames_received,
            total_frames_processed=s.total_frames_processed,
            avg_inference_ms=round(s.avg_inference_ms, 2),
            effective_fps=round(s.effective_fps, 1),
        )
        for s in _frame_skip_ctrl.all_stats()
    ]


@router.post("/cameras/{camera_id}/set-skip-rate")
def set_camera_skip_rate(
    camera_id: str,
    skip_rate: int = Query(..., ge=1, le=30, description="Process every Nth frame"),
):
    """
    Manually override the frame skip rate for a specific camera.

    Guidelines:
      - High-res cameras (4K):   skip_rate = 5–10
      - Standard cameras (1080p): skip_rate = 2–3
      - Low-res / edge devices:  skip_rate = 5 (recommended for Pi/NCS)
      - Server GPU:              skip_rate = 1 (process every frame)
    """
    # Simulate getting/creating stats for the camera
    _frame_skip_ctrl._get_or_create(camera_id).current_skip_rate = skip_rate
    return {
        "camera_id": camera_id,
        "skip_rate": skip_rate,
        "message": f"Frame skip rate set to {skip_rate} for {camera_id}. "
        f"Effective processing rate: 1 frame per {skip_rate}.",
    }


# ─────────────────────────────────────────────────────────────────
# Camera Config API  (conf_threshold / ROI / queue / classes / retries)
# ─────────────────────────────────────────────────────────────────

from app.lmp_tx.camera_config import CameraConfig, config_registry, COCO_CLASSES
from app.lmp_tx.frame_buffer import buffer_registry
from app.lmp_tx.reconnect import reconnect_registry
from pydantic import BaseModel as _BM
from typing import Optional as _Opt


class CameraConfigIn(_BM):
    """Request body for creating / updating a camera config."""

    camera_id: str
    url: str
    model: str = "yolov8n.pt"
    conf_threshold: float = 0.5
    roi: _Opt[list[int]] = None
    roi_polygon: _Opt[list[list[int]]] = None
    queue_size: int = 30
    classes: _Opt[list[int]] = None
    retries: int = 5
    auto_reconnect: bool = True
    frame_skip: int = 1


class CameraConfigOut(_BM):
    camera_id: str
    url: str
    model: str
    conf_threshold: float
    roi: _Opt[list[int]]
    roi_polygon: _Opt[list[list[int]]]
    queue_size: int
    classes: _Opt[list[int]]
    class_names: list[str]
    retries: int
    auto_reconnect: bool
    frame_skip: int
    warnings: list[str]


class BufferStatsOut(_BM):
    camera_id: str
    maxsize: int
    current_depth: int
    max_depth_seen: int
    total_enqueued: int
    total_dropped: int
    total_consumed: int
    drop_rate: float


class ReconnectStatsOut(_BM):
    camera_id: str
    total_reconnects: int
    total_failures: int
    consecutive_fails: int
    last_fail_reason: str


@router.post("/config", response_model=CameraConfigOut)
def set_camera_config(payload: CameraConfigIn):
    """
    Create or update the full config for one camera.

    All five inference-quality parameters are set here:
    • conf_threshold — ghost-detection suppression (0.4–0.6 recommended)
    • roi            — pixel bounding box [x1,y1,x2,y2] or None for full frame
    • queue_size     — FrameBuffer depth; prevents RTSP lag accumulation
    • classes        — COCO class IDs to keep (None = all)
    • retries        — auto-reconnect attempts on stream drop
    """
    cfg = CameraConfig(
        camera_id=payload.camera_id,
        url=payload.url,
        model=payload.model,
        conf_threshold=payload.conf_threshold,
        roi=payload.roi,
        roi_polygon=payload.roi_polygon,
        queue_size=payload.queue_size,
        classes=payload.classes,
        retries=payload.retries,
        auto_reconnect=payload.auto_reconnect,
        frame_skip=payload.frame_skip,
    )
    warnings = config_registry.set(cfg)
    # Pre-create buffer with the correct size
    buffer_registry.get_or_create(cfg.camera_id, maxsize=cfg.queue_size)
    return CameraConfigOut(
        **cfg.summary(),
        url=cfg.url,
        model=cfg.model,
        auto_reconnect=cfg.auto_reconnect,
        frame_skip=cfg.frame_skip,
        warnings=warnings,
    )


@router.get("/config/{camera_id}", response_model=CameraConfigOut)
def get_camera_config(camera_id: str):
    """Retrieve the current config for one camera."""
    cfg = config_registry.get(camera_id)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"No config for {camera_id}")
    return CameraConfigOut(
        **cfg.summary(),
        url=cfg.url,
        model=cfg.model,
        auto_reconnect=cfg.auto_reconnect,
        frame_skip=cfg.frame_skip,
        warnings=[],
    )


@router.get("/config", response_model=List[CameraConfigOut])
def list_camera_configs():
    """Return configs for all registered cameras."""
    return [
        CameraConfigOut(
            **c.summary(),
            url=c.url,
            model=c.model,
            auto_reconnect=c.auto_reconnect,
            frame_skip=c.frame_skip,
            warnings=[],
        )
        for c in config_registry.all()
    ]


@router.delete("/config/{camera_id}")
def delete_camera_config(camera_id: str):
    """Remove a camera config from the registry."""
    if not config_registry.delete(camera_id):
        raise HTTPException(status_code=404, detail=f"No config for {camera_id}")
    return {"detail": f"Config for {camera_id} deleted."}


@router.get("/config/yaml/export")
def export_yaml_config():
    """
    Export the entire camera config registry as a YAML string.
    The output format matches the project documentation example exactly.
    """
    try:
        yaml_str = config_registry.dump_yaml()
    except ImportError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"yaml": yaml_str}


@router.post("/config/yaml/import")
def import_yaml_config(yaml_content: str):
    """
    Bulk-import camera configs from a YAML string.
    Matches the documented config file format:

        camera_1:
          url: "rtsp://admin:pass@192.168.1.50:554/stream"
          conf_threshold: 0.5
          frame_skip: 5
          classes: [0, 2]
          roi: [100, 100, 500, 500]
          auto_reconnect: true
          queue_size: 30
          retries: 5
    """
    import io

    try:
        import yaml  # type: ignore
    except ImportError:
        raise HTTPException(status_code=500, detail="PyYAML not installed")

    try:
        raw = yaml.safe_load(io.StringIO(yaml_content)) or {}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

    results = {}
    for cam_id, params in raw.items():
        if not isinstance(params, dict):
            continue
        cfg = CameraConfig(
            camera_id=cam_id,
            url=params.get("url", ""),
            model=params.get("model", "yolov8n.pt"),
            conf_threshold=float(params.get("conf_threshold", 0.5)),
            roi=params.get("roi"),
            roi_polygon=params.get("roi_polygon"),
            queue_size=int(params.get("queue_size", 30)),
            classes=params.get("classes"),
            retries=int(params.get("retries", 5)),
            auto_reconnect=bool(params.get("auto_reconnect", True)),
            frame_skip=int(params.get("frame_skip", 1)),
        )
        warnings = config_registry.set(cfg)
        buffer_registry.get_or_create(cam_id, maxsize=cfg.queue_size)
        results[cam_id] = {"status": "registered", "warnings": warnings}

    return {"cameras_loaded": len(results), "details": results}


@router.get("/coco-classes")
def list_coco_classes():
    """
    Return the COCO class ID → name mapping for use in the classes filter.
    Use these IDs in the `classes` parameter of /lmp/config.
    """
    return {
        "classes": [{"id": k, "name": v} for k, v in sorted(COCO_CLASSES.items())],
        "example": "Set classes=[0,2] to detect only 'person' and 'car'.",
    }


# ─────────────────────────────────────────────────────────────────
# Buffer & Reconnect Diagnostics
# ─────────────────────────────────────────────────────────────────


@router.get("/diagnostics/buffers", response_model=List[BufferStatsOut])
def get_buffer_stats():
    """
    Live FrameBuffer statistics for all cameras.
    High drop_rate means the consumer (inference) can't keep up —
    increase frame_skip or lower resolution.
    """
    return [
        BufferStatsOut(
            camera_id=s.camera_id,
            maxsize=buffer_registry.get(s.camera_id).maxsize
            if buffer_registry.get(s.camera_id)
            else 0,
            current_depth=s.current_depth,
            max_depth_seen=s.max_depth_seen,
            total_enqueued=s.total_enqueued,
            total_dropped=s.total_dropped,
            total_consumed=s.total_consumed,
            drop_rate=round(s.drop_rate, 4),
        )
        for s in buffer_registry.all_stats()
    ]


@router.post("/diagnostics/buffers/{camera_id}/drain")
def drain_buffer(camera_id: str):
    """Manually drain the FrameBuffer for a camera (e.g. after a reconnect)."""
    buf = buffer_registry.get(camera_id)
    if not buf:
        raise HTTPException(status_code=404, detail=f"No buffer for {camera_id}")
    dropped = buf.drain()
    return {"camera_id": camera_id, "frames_drained": dropped}


@router.get("/diagnostics/reconnects", response_model=List[ReconnectStatsOut])
def get_reconnect_stats():
    """
    Reconnect controller statistics — shows how often each camera
    has dropped and been automatically recovered.
    """
    return [
        ReconnectStatsOut(
            camera_id=s.camera_id,
            total_reconnects=s.total_reconnects,
            total_failures=s.total_failures,
            consecutive_fails=s.consecutive_fails,
            last_fail_reason=s.last_fail_reason,
        )
        for s in reconnect_registry.all_stats()
    ]
