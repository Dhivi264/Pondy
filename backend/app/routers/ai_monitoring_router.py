"""
AI Unified Monitoring & Health Router
Exposes comprehensive AI system status including:
- Watchdog self-healing metrics
- Multi-camera fusion global tracking
- Detector & Tracker health
- Model inference latency
- Security threat detection
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth import get_current_user
from app.models.user import User
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Monitoring"], prefix="/ai")


# ─────────────────────────────────────────────────────────────────────────────
# AI HEALTH & WATCHDOG STATUS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/health/watchdog")
async def get_watchdog_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive Watchdog self-healing AI metrics.
    Includes recovery counts, learning progress, repair history.
    """
    try:
        from app.ai.watchdog import watchdog
        
        report = watchdog.get_repair_report()
        return {
            "status": report.get("status"),
            "is_active": report.get("is_self_healing_active"),
            "last_scan_ts": report.get("last_scan_ts"),
            "recovery_metrics": {
                "ai_threads_recovered": report.get("recovered_ai_threads"),
                "db_connections_recovered": report.get("recovered_db_sessions"),
                "camera_resets": report.get("camera_resets"),
                "model_reloads": report.get("model_reloads"),
                "security_blocks_applied": report.get("security_blocks_applied"),
                "throttling_adjustments": report.get("throttling_adjustments"),
            },
            "learning": {
                "successful_learns_this_month": report.get("successful_learns_this_month"),
                "monthly_goal": report.get("monthly_goal"),
                "progress": report.get("learning_progress"),
            },
            "knowledge_base_size": report.get("knowledge_base_size"),
            "repair_history_recent": report.get("repair_history", [])[-10:],  # Last 10 entries
        }
    except Exception as e:
        logger.error(f"[AI Health] Watchdog status fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Watchdog status unavailable")


@router.get("/health/detector")
async def get_detector_health(
    current_user: User = Depends(get_current_user)
):
    """Get real-time Detector (YOLO11) health metrics."""
    try:
        from app.workers.stream_worker import stream_worker
        
        health = {
            "status": "healthy" if stream_worker.is_running else "stopped",
            "model": "YOLO11",
            "is_running": stream_worker.is_running,
        }
        
        # Get detector health if available
        if hasattr(stream_worker, 'detector') and stream_worker.detector:
            detector_health = stream_worker.detector.get_health()
            health.update({
                "device": detector_health.get("device"),
                "tracker_type": detector_health.get("tracker_type"),
                "avg_latency_ms": detector_health.get("avg_latency_ms"),
                "inference_count": detector_health.get("inference_count"),
                "error_rate": detector_health.get("error_rate"),
                "last_inference_age_seconds": detector_health.get("last_inference_age"),
            })
        
        # Add telemetry
        if hasattr(stream_worker, 'telemetry'):
            health["telemetry"] = {
                "detections_total": stream_worker.telemetry.get("detections_total", 0),
                "recognitions_total": stream_worker.telemetry.get("recognitions_total", 0),
            }
        
        return health
    except Exception as e:
        logger.error(f"[AI Health] Detector health fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Detector health unavailable")


@router.get("/health/tracker")
async def get_tracker_health(
    current_user: User = Depends(get_current_user)
):
    """Get Tracker state and statistics per camera."""
    try:
        from app.workers.stream_worker import stream_worker
        
        stats = {}
        if hasattr(stream_worker, 'tracker'):
            stats = stream_worker.tracker.get_stats()
        
        return {
            "status": "active" if stream_worker.is_running else "inactive",
            "camera_states": stats,
            "total_cameras_tracked": len(stats),
        }
    except Exception as e:
        logger.error(f"[AI Health] Tracker health fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Tracker health unavailable")


# ─────────────────────────────────────────────────────────────────────────────
# MULTI-CAMERA FUSION STATUS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/fusion/status")
async def get_fusion_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get multi-camera tracking fusion status.
    Includes global ID assignments, cross-camera matches, active persons.
    """
    try:
        from app.ai.multi_camera_fusion import multi_camera_fusion
        
        stats = multi_camera_fusion.get_fusion_stats()
        
        return {
            "status": "active",
            "active_global_tracks": stats.get("active_global_tracks"),
            "total_global_ids_ever": stats.get("total_global_ids_ever"),
            "fusion_events_total": stats.get("fusion_events"),
            "id_assignments": stats.get("id_assignments"),
            "reid_matches": stats.get("reid_matches"),
            "last_fusion_time": stats.get("last_fusion"),
            "camera_count": len(multi_camera_fusion.camera_topology),
        }
    except Exception as e:
        logger.error(f"[Fusion] Status fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Fusion status unavailable")


@router.get("/fusion/global-tracks")
async def get_global_tracks(
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    """Get currently active global person tracks across all cameras."""
    try:
        from app.ai.multi_camera_fusion import multi_camera_fusion
        from datetime import datetime
        
        tracks_list = []
        for global_id, track in list(multi_camera_fusion.global_tracks.items())[:limit]:
            track_info = {
                "global_id": global_id,
                "local_track_id": track.local_track_id,
                "camera_id": track.camera_id,
                "employee_id": track.employee_id,
                "confidence": round(track.confidence, 3),
                "first_seen": track.first_seen.isoformat(),
                "last_seen": track.last_seen.isoformat(),
                "duration_seconds": (track.last_seen - track.first_seen).total_seconds(),
            }
            tracks_list.append(track_info)
        
        return {
            "total_active": len(multi_camera_fusion.global_tracks),
            "returned": len(tracks_list),
            "tracks": tracks_list,
        }
    except Exception as e:
        logger.error(f"[Fusion] Global tracks fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Global tracks unavailable")


# ─────────────────────────────────────────────────────────────────────────────
# COMPREHENSIVE AI SYSTEM STATUS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/status/full")
async def get_full_ai_status(
    current_user: User = Depends(get_current_user)
):
    """
    Complete AI system status dashboard.
    Combines Watchdog, Detector, Tracker, and Fusion into one comprehensive view.
    """
    try:
        from app.workers.stream_worker import stream_worker
        from app.ai.watchdog import watchdog
        from app.ai.multi_camera_fusion import multi_camera_fusion
        
        # Get all components
        watchdog_report = watchdog.get_repair_report()
        detector_health = stream_worker.detector.get_health() if hasattr(stream_worker, 'detector') else {}
        tracker_stats = stream_worker.tracker.get_stats() if hasattr(stream_worker, 'tracker') else {}
        fusion_stats = multi_camera_fusion.get_fusion_stats()
        
        return {
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "overall_status": "healthy" if stream_worker.is_running and watchdog._running else "degraded",
            "components": {
                "watchdog": {
                    "active": watchdog._running,
                    "recovered_cameras": watchdog_report.get("recovered_ai_threads"),
                    "learned_fixes": watchdog_report.get("successful_learns_this_month"),
                    "knowledge_base_size": watchdog_report.get("knowledge_base_size"),
                    "last_repair": watchdog_report.get("repair_history", [])[-1] if watchdog_report.get("repair_history") else None,
                },
                "detector": {
                    "status": "running" if stream_worker.is_running else "stopped",
                    "model": "YOLO11",
                    "device": detector_health.get("device"),
                    "avg_latency_ms": detector_health.get("avg_latency_ms"),
                    "error_rate": detector_health.get("error_rate"),
                    "tracker": detector_health.get("tracker_type"),
                },
                "tracker": {
                    "status": "active" if stream_worker.is_running else "inactive",
                    "cameras_tracked": len(tracker_stats),
                    "active_tracks": sum(s.get("active_tracks", 0) for s in tracker_stats.values()),
                },
                "fusion": {
                    "status": "active",
                    "global_ids_active": fusion_stats.get("active_global_tracks"),
                    "total_global_ids": fusion_stats.get("total_global_ids_ever"),
                    "reid_match_rate": fusion_stats.get("reid_matches"),
                },
                "pipeline": {
                    "stream_worker_running": stream_worker.is_running,
                    "cameras_active": len(tracker_stats),
                },
            },
            "performance": {
                "detections_total": stream_worker.telemetry.get("detections_total", 0) if hasattr(stream_worker, 'telemetry') else 0,
                "memory_pressure": stream_worker.telemetry.get("memory_pressure", "normal") if hasattr(stream_worker, 'telemetry') else "unknown",
            },
        }
    except Exception as e:
        logger.error(f"[AI Status] Full status fetch failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI status unavailable: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY & THREAT STATUS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/security/threats")
async def get_security_threats(
    current_user: User = Depends(get_current_user)
):
    """Get recent security threats detected by Watchdog."""
    try:
        from app.ai.watchdog import watchdog
        
        threats = []
        # Parse history for security-related repairs
        for entry in watchdog._history[-50:]:  # Last 50 entries
            if "security" in entry.lower() or "threat" in entry.lower() or "anomaly" in entry.lower():
                threats.append(entry)
        
        return {
            "recent_threats": threats[-10:],  # Last 10 threats
            "security_blocks_applied": watchdog._recovery_counts.get("security_blocks", 0),
            "status": "secure" if not threats else "investigating",
        }
    except Exception as e:
        logger.error(f"[Security] Threat fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Security status unavailable")


# ─────────────────────────────────────────────────────────────────────────────
# AI CONTROL ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/watchdog/toggle")
async def toggle_watchdog(
    active: bool,
    current_user: User = Depends(get_current_user)
):
    """Start or stop the Watchdog self-healing system."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        from app.ai.watchdog import watchdog
        
        if active and not watchdog._running:
            watchdog.start()
            return {"status": "watchdog_started", "message": "Self-healing AI watchdog activated"}
        elif not active and watchdog._running:
            watchdog.stop()
            return {"status": "watchdog_stopped", "message": "Self-healing AI watchdog deactivated"}
        else:
            return {"status": "no_change", "message": f"Watchdog already {'running' if active else 'stopped'}"}
    except Exception as e:
        logger.error(f"[Watchdog Control] Toggle failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fusion/camera-topology")
async def get_fusion_camera_topology(
    current_user: User = Depends(get_current_user)
):
    """Get camera adjacency topology for multi-camera fusion."""
    try:
        from app.ai.multi_camera_fusion import multi_camera_fusion
        
        return {
            "topology": multi_camera_fusion.camera_topology,
            "cameras_configured": len(multi_camera_fusion.camera_topology),
        }
    except Exception as e:
        logger.error(f"[Fusion] Topology fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Topology unavailable")


@router.post("/fusion/set-camera-topology")
async def set_fusion_camera_topology(
    topology: Dict[str, List[str]],
    current_user: User = Depends(get_current_user)
):
    """Configure camera adjacency for better fusion decisions."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        from app.ai.multi_camera_fusion import multi_camera_fusion
        
        multi_camera_fusion.register_camera_topology(topology)
        return {
            "status": "topology_configured",
            "cameras": len(topology),
        }
    except Exception as e:
        logger.error(f"[Fusion] Topology set failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
