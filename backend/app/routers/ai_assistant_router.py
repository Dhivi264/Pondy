"""
AI Assistant Router
--------------------
POST /ai/ask  — context-aware answers, live system data, person camera-trail lookup
GET  /ai/health — quick system snapshot
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Tuple
import datetime
import re

from app.db import get_db
from app.auth import get_current_user
from app.models.user import User

router = APIRouter(tags=["AI Assistant"])


# ─── Schemas ──────────────────────────────────────────────────────────────────


class AskRequest(BaseModel):
    question: str
    conversation_history: Optional[List[dict]] = []


class AskResponse(BaseModel):
    answer: str
    intent: str
    data_snapshot: Optional[dict] = None
    suggestions: List[str] = []


# ─── Person / ID extraction helpers ───────────────────────────────────────────


def _extract_id_from_question(q: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Tries to pull either:
      • a numeric DB id  → (123, None)
      • an employee_code string like EMP001 / FACE-007 / person_42
        → (None, "EMP001")
    Returns (numeric_id, code_string) — at most one will be non-None.
    """
    # Numeric ID anywhere in the string
    numeric = re.search(r"\b(\d{1,6})\b", q)
    # Alphanumeric employee code pattern
    code = re.search(r"\b([A-Za-z]+[-_]?\d+|[A-Za-z]{2,}\d{3,})\b", q)
    num_id = int(numeric.group(1)) if numeric else None
    code_str = code.group(1).upper() if code else None
    return num_id, code_str


def _question_is_person_lookup(q: str) -> bool:
    """Return True when the question is asking about a specific person's camera trail."""
    triggers = [
        "where",
        "which camera",
        "camera.*pass",
        "pass.*camera",
        "seen",
        "spotted",
        "sighting",
        "trail",
        "track",
        "path",
        "visit",
        "appear",
        "went",
        "location of",
        "show me",
        "find",
        "face_id",
        "person_id",
        "employee_id",
        "emp id",
        "face id",
    ]
    q_low = q.lower()
    return any(t in q_low for t in triggers) and bool(re.search(r"\d+|[A-Z]{2,}\d+", q))


# ─── Live data — person camera trail ──────────────────────────────────────────


def _lookup_person_trail(db: Session, question: str) -> Optional[dict]:
    """
    Resolve an employee from the question text and return their camera trail.
    Returns None if no employee can be identified.
    """
    from app.models.employee import Employee
    from app.models.tracking import PersonSighting
    from app.models.attendance import CameraPresenceSummary, AttendanceSession
    from app.models.camera import Camera

    num_id, code_str = _extract_id_from_question(question)

    # 1. Find the employee ─────────────────────────────────────────────────────
    employee = None
    if num_id:
        employee = db.query(Employee).filter(Employee.id == num_id).first()
    if employee is None and code_str:
        employee = db.query(Employee).filter(Employee.employee_code == code_str).first()
    # Fuzzy name match fallback for queries like "where is John"
    if employee is None:
        for word in question.split():
            if len(word) >= 3 and word.isalpha():
                found = (
                    db.query(Employee).filter(Employee.name.ilike(f"%{word}%")).first()
                )
                if found:
                    employee = found
                    break

    if employee is None:
        return None  # Caller will fall through to normal intent handling

    # 2. Build camera map ──────────────────────────────────────────────────────
    all_cameras = {c.id: c for c in db.query(Camera).all()}

    # 2a. PersonSighting records (all-time, ordered by first_seen desc)
    sightings = (
        db.query(PersonSighting)
        .filter(PersonSighting.employee_id == employee.id)
        .order_by(PersonSighting.first_seen.desc())
        .limit(100)
        .all()
    )

    # 2b. CameraPresenceSummary (daily summaries)
    daily_summaries = (
        db.query(CameraPresenceSummary)
        .filter(CameraPresenceSummary.employee_id == employee.id)
        .order_by(CameraPresenceSummary.attendance_date.desc())
        .limit(60)
        .all()
    )

    # 2c. Today's AttendanceSession
    today = datetime.date.today()
    today_session = (
        db.query(AttendanceSession)
        .filter(
            AttendanceSession.employee_id == employee.id,
            AttendanceSession.attendance_date == today,
        )
        .first()
    )

    # 3. Aggregate per-camera stats ────────────────────────────────────────────
    cam_stats: dict = {}  # camera_id → { name, location, sightings, first_seen, last_seen, total_sec }

    def _update(cam_id, first_s, last_s, dur_sec=0):
        if cam_id is None:
            return
        cam = all_cameras.get(cam_id)
        if cam_id not in cam_stats:
            cam_stats[cam_id] = {
                "camera_id": cam_id,
                "name": cam.name if cam else f"Camera #{cam_id}",
                "location": cam.location if (cam and cam.location) else "—",
                "is_entry": cam.is_entry_camera if cam else False,
                "is_exit": cam.is_exit_camera if cam else False,
                "sightings": 0,
                "total_seconds": 0,
                "first_seen": None,
                "last_seen": None,
            }
        s = cam_stats[cam_id]
        s["sightings"] += 1
        s["total_seconds"] += dur_sec
        if first_s:
            if s["first_seen"] is None or first_s < s["first_seen"]:
                s["first_seen"] = first_s
        if last_s:
            if s["last_seen"] is None or last_s > s["last_seen"]:
                s["last_seen"] = last_s

    for sg in sightings:
        _update(sg.camera_id, sg.first_seen, sg.last_seen, sg.duration_seconds or 0)

    for ds in daily_summaries:
        _update(
            ds.camera_id, ds.first_seen, ds.last_seen, ds.total_visible_seconds or 0
        )

    if today_session:
        if today_session.entry_camera_id:
            _update(
                today_session.entry_camera_id,
                today_session.entry_time,
                today_session.entry_time,
            )
        if today_session.exit_camera_id:
            _update(
                today_session.exit_camera_id,
                today_session.exit_time,
                today_session.exit_time,
            )

    # Sort by last_seen desc
    trail = sorted(
        cam_stats.values(),
        key=lambda x: x["last_seen"] or datetime.datetime.min,
        reverse=True,
    )

    return {
        "employee": {
            "id": employee.id,
            "name": employee.name,
            "employee_code": employee.employee_code,
            "department": employee.department or "—",
            "designation": getattr(employee, "designation", "—"),
        },
        "trail": trail,
        "today_session": {
            "status": today_session.attendance_status if today_session else "no record",
            "entry_time": str(today_session.entry_time)
            if today_session and today_session.entry_time
            else None,
            "exit_time": str(today_session.exit_time)
            if today_session and today_session.exit_time
            else None,
            "entry_camera": today_session.entry_camera_id if today_session else None,
            "exit_camera": today_session.exit_camera_id if today_session else None,
        }
        if today_session
        else None,
        "total_cameras_visited": len(trail),
        "total_sightings": sum(c["sightings"] for c in trail),
        "total_duration_today": today_session.total_visible_duration_seconds
        if today_session
        else 0,
    }


def _format_trail_answer(data: dict) -> Tuple[str, List[str]]:
    """Turn a trail dict into a nicely formatted markdown answer with tables."""
    emp = data["employee"]
    trail = data["trail"]
    sess = data.get("today_session")

    # Header
    answer = (
        f"👤 **Employee Activity Report: {emp['name'].upper()}**\n"
        f"Employee Code: `{emp['employee_code']}` · ID: `#{emp['id']}`\n"
        f"Dept: {emp['department']} | Role: {emp.get('designation', '—')}\n\n"
    )

    # 📍 Current Location
    if trail:
        latest = trail[0]
        answer += (
            f"📍 **Current/Last Known Location:**\n"
            f"**{latest['name']}** — _{latest['location']}_\n"
            f"Last spotted: `{latest['last_seen'].strftime('%H:%M:%S') if latest['last_seen'] else '—'}`\n\n"
        )
    else:
        answer += "📍 **Location:** Not spotted on any cameras yet.\n\n"

    # 🗓️ Today's session
    if sess:
        status_icon = {"present": "🟢", "late": "🟡", "absent": "🔴"}.get(
            sess["status"].lower(), "⚪"
        )
        answer += f"🗓️ **Today's Status:** {status_icon} {sess['status'].upper()}\n"
        if sess.get("entry_time"):
            answer += f"  🚪 **First Seen:** `{sess['entry_time']}`\n"
        if sess.get("exit_time"):
            answer += f"  🚪 **Last Seen:**  `{sess['exit_time']}`\n"

        # TIME LIMIT / DURATION
        total_sec = data.get("total_duration_today", 0)
        m, s = divmod(total_sec, 60)
        h, m = divmod(m, 60)
        dur_str = f"{h}h {m}m" if h > 0 else f"{m}m {s}s"
        answer += f"  ⏳ **Total Time Limit Spent:** `{dur_str}`\n\n"
    else:
        answer += "🗓️ **Today's Status:** No attendance record found.\n\n"

    # 📷 Camera Trail Table
    if not trail:
        answer += "📷 **Camera Trail:** No sightings recorded.\n"
    else:
        answer += "📊 **Camera Pass History:**\n\n"
        answer += "| Camera | Location | Sightings | Duration | Last Seen |\n"
        answer += "| :--- | :--- | :---: | :---: | :--- |\n"

        for c in trail:
            last = "—"
            if c["last_seen"]:
                ls = c["last_seen"]
                if isinstance(ls, str):
                    ls = datetime.datetime.fromisoformat(ls)
                last = ls.strftime("%Y-%m-%d %H:%M")

            dur = "—"
            if c["total_seconds"] > 0:
                m, s = divmod(c["total_seconds"], 60)
                dur = f"{m}m {s}s"

            # Escape pipes if any (unlikely in camera names/locations)
            c_name = c["name"].replace("|", "｜")
            c_loc = c["location"].replace("|", "｜")

            answer += f"| {c_name} | {c_loc} | {c['sightings']} | {dur} | {last} |\n"

        answer += "\n"

    suggestions = [
        "Show employee list",
        "Recent anomalies",
        "System dashboard",
    ]
    return answer, suggestions


# ─── Live data — full system snapshot ─────────────────────────────────────────


def _collect_system_snapshot(db: Session) -> dict:
    snap: dict = {}

    try:
        from app.models.camera import Camera

        cameras = db.query(Camera).all()
        online = [c for c in cameras if c.status == "online"]
        snap["cameras"] = {
            "total": len(cameras),
            "online": len(online),
            "offline": len(cameras) - len(online),
            "list": [
                {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "location": getattr(c, "location", "—"),
                }
                for c in cameras
            ],
        }
    except Exception as e:
        snap["cameras"] = {"error": str(e)}

    try:
        from app.models.employee import Employee

        employees = db.query(Employee).filter(Employee.is_active).all()
        enrolled = (
            db.query(Employee)
            .join(Employee.face_templates)
            .filter(Employee.is_active)
            .distinct()
            .count()
        )
        snap["employees"] = {
            "total": len(employees),
            "enrolled": enrolled,
            "list": [
                {
                    "id": e.id,
                    "name": e.name,
                    "employee_code": e.employee_code,
                    "department": getattr(e, "department", "—"),
                    "has_face": bool(getattr(e, "face_templates", [])),
                }
                for e in employees
            ],
        }
    except Exception as e:
        snap["employees"] = {"error": str(e)}

    try:
        from app.models.attendance import AttendanceSession

        today = datetime.date.today()
        sessions = (
            db.query(AttendanceSession)
            .filter(AttendanceSession.attendance_date == today)
            .all()
        )
        snap["attendance"] = {
            "date": str(today),
            "present": sum(
                1 for s in sessions if s.attendance_status in ("present", "Present")
            ),
            "late": sum(1 for s in sessions if s.attendance_status in ("late", "Late")),
            "absent": sum(
                1 for s in sessions if s.attendance_status in ("absent", "Absent")
            ),
            "total_sessions": len(sessions),
        }
    except Exception as e:
        snap["attendance"] = {"date": str(datetime.date.today()), "error": str(e)}

    try:
        from app.workers.stream_worker import stream_worker

        snap["ai_pipeline"] = {
            "running": stream_worker._running,
            "active_threads": len(stream_worker._threads),
            "camera_ids": list(stream_worker._threads.keys()),
        }
    except Exception as e:
        snap["ai_pipeline"] = {"error": str(e)}

    try:
        from app.models.archive import ArchiveRecord

        snap["archive"] = {"total_records": db.query(ArchiveRecord).count()}
    except Exception as e:
        snap["archive"] = {"error": str(e)}

    try:
        from app.ai.watchdog import watchdog

        snap["self_healing"] = watchdog.get_repair_report()
    except Exception as e:
        snap["self_healing"] = {"error": str(e)}

    snap["queried_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    return snap


# ─── Intent detection ─────────────────────────────────────────────────────────


def _detect_intent(q: str) -> str:
    ql = q.lower()
    # Person trail intent — must be checked first
    if _question_is_person_lookup(q):
        return "person_trail"
    if any(w in ql for w in ["camera", "stream", "feed", "offline", "online", "live"]):
        return "cameras"
    if any(
        w in ql for w in ["attend", "present", "absent", "late", "check-in", "check in"]
    ):
        return "attendance"
    if any(w in ql for w in ["employee", "staff", "worker", "enroll"]):
        return "employees"
    if any(
        w in ql
        for w in ["face_id", "person_id", "face id", "person id", "who is", "where is"]
    ):
        return "person_trail"
    if any(
        w in ql
        for w in ["ai", "pipeline", "yolo", "detect", "recogni", "engine", "model"]
    ):
        return "ai_pipeline"
    if any(w in ql for w in ["anomal", "alert", "warning", "critical"]):
        return "anomalies"
    if any(w in ql for w in ["archive", "recording", "clip", "video"]):
        return "archive"
    if any(w in ql for w in ["health", "status", "overview", "summary", "dashboard"]):
        return "dashboard"
    if any(w in ql for w in ["repair", "healing", "watchdog", "recovery", "fix"]):
        return "self_healing"
    return "general"


# ─── Answer builder ───────────────────────────────────────────────────────────


def _build_answer(
    question: str, intent: str, snap: dict, db: Optional[Session] = None
) -> Tuple[str, List[str]]:
    q = question.lower().strip()

    # ── Person camera trail ───────────────────────────────────────────────────
    if intent == "person_trail" and db is not None:
        try:
            trail_data = _lookup_person_trail(db, question)
            if trail_data is not None:
                return _format_trail_answer(trail_data)
        except Exception as e:
            return (
                f"[WARNING] Could not look up person trail: {e}\n\n"
                'Try: *"where has employee #5 been?"* or *"cameras for EMP001"*',
                ["System overview", "Show employees"],
            )
        # If no employee found, fall through to helpful message
        num_id, code_str = _extract_id_from_question(question)
        hint = (
            f"`#{num_id}`" if num_id else f"`{code_str}`" if code_str else "that person"
        )
        return (
            f"[SEARCH] I couldn't find an employee matching {hint} in the database.\n\n"
            f"**Try these formats:**\n"
            f'  • *"Where has employee #5 been?"* — search by DB ID\n'
            f'  • *"Cameras for EMP001"* — search by employee code\n'
            f'  • *"Show trail for John"* — search by name\n\n'
            f"Use the **Employees** screen to find the correct ID or code.",
            ["Show employees", "System overview"],
        )

    # ── Dashboard / overview ──────────────────────────────────────────────────
    if intent == "dashboard":
        cams = snap.get("cameras", {})
        att = snap.get("attendance", {})
        emp = snap.get("employees", {})
        ai = snap.get("ai_pipeline", {})
        answer = (
            f"[SYSTEM] **System Overview** — {snap.get('queried_at', 'now')}\n\n"
            f"**Cameras:** {cams.get('online', '?')}/{cams.get('total', '?')} online"
            f" ({cams.get('offline', 0)} offline)\n"
            f"**Employees:** {emp.get('total', '?')} active, {emp.get('enrolled', '?')} face-enrolled\n"
            f"**Attendance today ({att.get('date', '—')}):** "
            f"{att.get('present', '?')} present · {att.get('late', 0)} late · "
            f"{att.get('absent', 0)} absent\n"
            f"**AI Pipeline:** {'[RUNNING]' if ai.get('running') else '[STOPPED]'}"
            f" ({ai.get('active_threads', 0)} active threads)\n"
            f"**Archive:** {snap.get('archive', {}).get('total_records', '?')} records\n"
        )
        return answer, ["Show camera list", "Check AI pipeline", "Today's attendance"]

    # ── Cameras ───────────────────────────────────────────────────────────────
    if intent == "cameras":
        cams = snap.get("cameras", {})
        if "error" in cams:
            return f"[WARNING] Camera data unavailable: {cams['error']}", []
        if "offline" in q:
            offline = [c for c in cams.get("list", []) if c["status"] != "online"]
            if not offline:
                return "[OK] All cameras are currently **online**.", [
                    "Start AI pipeline",
                    "System overview",
                ]
            names = "\n".join(
                f"  • #{c['id']} **{c['name']}** — {c['location']}" for c in offline
            )
            return (
                f"[OFFLINE] **{len(offline)} offline camera(s):**\n{names}\n\n"
                "Check RTSP stream URL or physical connection."
            ), ["Go to Cameras"]
        cam_list = "\n".join(
            f"  {'[ONLINE]' if c['status'] == 'online' else '[OFFLINE]'} #{c['id']} **{c['name']}** "
            f"({c['location']}) — {c['status']}"
            for c in cams.get("list", [])
        )
        return (
            f"[CAMERA] **Camera Status** ({cams.get('online', 0)}/{cams.get('total', 0)} online)\n\n"
            f"{cam_list or 'No cameras registered.'}",
            ["Show offline cameras", "Start AI pipeline", "System overview"],
        )

    # ── Employees ─────────────────────────────────────────────────────────────
    if intent == "employees":
        emp = snap.get("employees", {})
        if "error" in emp:
            return f"[WARNING] Employee data unavailable: {emp['error']}", []
        if "enroll" in q:
            not_en = [e for e in emp.get("list", []) if not e["has_face"]]
            if not not_en:
                return "[OK] All employees have face templates enrolled.", [
                    "Today's attendance"
                ]
            names = "\n".join(
                f"  • #{e['id']} **{e['name']}** ({e['employee_code']})"
                for e in not_en[:10]
            )
            return (
                f"[WARNING] **{len(not_en)} without face enrollment:**\n{names}\n\n"
                "Go to Employees → select → Enroll Face."
            ), ["Go to Employees"]
        by_dept: dict = {}
        for e in emp.get("list", []):
            by_dept.setdefault(e.get("department") or "Unknown", []).append(e["name"])
        dept_lines = "\n".join(f"  • **{d}**: {len(v)}" for d, v in by_dept.items())
        return (
            f"👤 **Employee Summary** — {emp.get('total', 0)} active\n"
            f"Face-enrolled: {emp.get('enrolled', 0)}/{emp.get('total', 0)}\n\n"
            f"**By Department:**\n{dept_lines or '  No data'}",
            ["Who is not enrolled?", "Today's attendance", "System overview"],
        )

    # ── Attendance ────────────────────────────────────────────────────────────
    if intent == "attendance":
        att = snap.get("attendance", {})
        emp_total = snap.get("employees", {}).get("total", 0)
        if "error" in att:
            return f"⚠️ Attendance data unavailable: {att['error']}", []
        present = att.get("present", 0)
        late = att.get("late", 0)
        absent = att.get("absent", 0)
        pct = round(present / emp_total * 100) if emp_total else 0
        return (
            f"📋 **Attendance — {att.get('date', 'today')}**\n\n"
            f"  🟢 Present : **{present}**\n"
            f"  🟡 Late    : **{late}**\n"
            f"  🔴 Absent  : **{absent}**\n"
            f"  📊 Presence rate: **{pct}%**\n\n"
            f"Tracked automatically via YOLOv11 face recognition on entry cameras.",
            ["Show employees", "System overview"],
        )

    # ── Self-Healing / Repair ─────────────────────────────────────────────────
    if intent == "repair" or "watchdog" in q:
        ai = snap.get("ai_pipeline", {})
        repair = ai.get("self_healing", {})
        total_rep = (
            sum(repair.get("repaired", {}).values())
            if isinstance(repair.get("repaired"), dict)
            else 0
        )
        answer = (
            f"🛠️ **Self-Healing Engine (Watchdog) Status**\n\n"
            f"**Engine Health:** {'🟢 Healthy' if repair.get('is_running') else '🔴 Monitoring Stopped'}\n"
            f"**Auto-Throttling:** {'Autonomous' if ai.get('dynamic_throttling') else 'Fixed'}\n"
            f"**Total AI Recoveries:** {total_rep}\n"
            f"**Scan Frequency:** every 20s\n\n"
            f"The Watchdog is currently monitoring **{ai.get('active_threads', 0)}** neural threads. "
            f"If it detects a hung RTSP stream or DB stall, it will autonomously re-calibrate the pipeline."
        )
        return answer, ["Check AI pipeline", "Show camera list", "System overview"]

    # ── AI Pipeline ───────────────────────────────────────────────────────────
    if intent == "ai_pipeline":
        ai = snap.get("ai_pipeline", {})
        if "error" in ai:
            return f"⚠️ AI pipeline status unavailable: {ai['error']}", []
        running = ai.get("running", False)
        status_icon = "🟢" if running else "🔴"
        answer = (
            f"{status_icon} **AI Pipeline is {'RUNNING' if running else 'STOPPED'}**\n\n"
            f"Active camera threads: **{ai.get('active_threads', 0)}**\n"
            f"Processing cameras: {ai.get('camera_ids', []) or 'None'}\n\n"
        )
        if not running:
            answer += (
                "**To start:**\n"
                "  • Dashboard → System Controls → Start AI\n"
                "  • Or call `POST /lmp/system/start-ai`"
            )
            return answer, ["Start AI engine", "System overview", "Show cameras"]
        answer += (
            "**Stack:**\n"
            "  🔸 **YOLOv11n** — person & object detection\n"
            "  🔸 **ByteTrack** — multi-object tracking\n"
            "  🔸 **YOLOv11n-face + ONNX** — face detection & embedding\n"
            "  🔸 Cosine similarity gallery match → employee identification"
        )
        return answer, ["Face recognition info", "System overview"]

    # ── Archive ───────────────────────────────────────────────────────────────
    if intent == "archive":
        total = snap.get("archive", {}).get("total_records", 0)
        return (
            f"🗂️ **Archive** — **{total}** recorded events\n\n"
            "Stores AI-flagged events: entry/exit clips, unknown faces, anomalies.\n"
            "Go to **Archive** in the sidebar to review and export.",
            ["System overview"],
        )

    # ── Anomalies ─────────────────────────────────────────────────────────────
    if intent == "anomalies":
        return (
            "🚨 **Anomaly Detection**\n\n"
            "Anomalies are flagged when:\n"
            "  • An unknown face is spotted repeatedly\n"
            "  • A person lingers in a restricted zone\n"
            "  • Entry/exit patterns deviate from baseline\n\n"
            "View all in **LMP-TX** → Anomaly Feed.",
            ["AI pipeline status", "System overview"],
        )

    # ── Self Healing ────────────────────────────────────────────────────────
    if intent == "self_healing":
        sh = snap.get("self_healing", {})
        if "error" in sh:
            return f"⚠️ Self-repair system is offline: {sh['error']}", []

        recovered_threads = sh.get("recovered_ai_threads", 0)
        status = "Active 🛡️" if sh.get("is_self_healing_active") else "Inactive ⚪"

        answer = (
            f"🛡️ **System Self-Repair Status: {status}**\n\n"
            f"The AI Watchdog is monitoring all 24/7 surveillance threads.\n"
            f"  • **Recovered Processor Threads:** {recovered_threads}\n"
            f"  • **Recovered Database Sessions:** {sh.get('recovered_db_sessions', 0)}\n"
            f"  • **Last Diagnostic Scan:** {datetime.datetime.fromtimestamp(sh.get('last_scan_ts', 0)).strftime('%H:%M:%S')}\n\n"
            "The system is configured for automated recovery. If a camera thread crashes, I will restart it within 30 seconds."
        )
        return answer, ["Full system snapshot", "Check AI pipeline"]

    # ── Help ──────────────────────────────────────────────────────────────────
    if intent == "help":
        return (
            "👋 **Smart CCTV AI Assistant** — I can help with:\n\n"
            "  📷 **Cameras** — status, online/offline\n"
            "  👤 **Employees** — list, face enrollment\n"
            "  📋 **Attendance** — present/absent/late today\n"
            "  🔍 **Person trail** — which cameras a person passed\n"
            "  🤖 **AI Pipeline** — YOLO11 status, model info\n"
            "  🗂️ **Archive** — recorded event count\n"
            "  📊 **Dashboard** — full system overview\n\n"
            '**Try:** *"Where has employee #3 been?"* or *"Cameras for EMP001"*',
            [
                "System overview",
                "Show cameras",
                "Today's attendance",
                "AI pipeline status",
            ],
        )

    # ── General fallback ──────────────────────────────────────────────────────
    cams = snap.get("cameras", {})
    att = snap.get("attendance", {})
    ai = snap.get("ai_pipeline", {})
    return (
        f'🤖 I received: *"{question}"*\n\n'
        f"Quick snapshot:\n"
        f"  • Cameras: {cams.get('online', '?')}/{cams.get('total', '?')} online\n"
        f"  • Attendance today: {att.get('present', '?')} present\n"
        f"  • AI engine: {'running' if ai.get('running') else 'stopped'}\n\n"
        "**Person trail examples:**\n"
        '  • *"Where has employee #5 been?"*\n'
        '  • *"Which cameras did EMP001 pass?"*\n'
        '  • *"Show trail for John"*',
        ["System overview", "Show cameras", "Today's attendance"],
    )


# ─── Routes ───────────────────────────────────────────────────────────────────


@router.post("/ai/ask", response_model=AskResponse)
async def ask_assistant(
    req: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Main AI assistant endpoint.
    Detects intent, queries live DB data, and returns a context-aware answer.
    Supports person-ID / face-ID lookup → full camera trail.
    """
    snap = _collect_system_snapshot(db)
    intent = _detect_intent(req.question)
    answer, suggestions = _build_answer(req.question, intent, snap, db=db)

    return AskResponse(
        answer=answer,
        intent=intent,
        data_snapshot=snap,
        suggestions=suggestions,
    )


@router.get("/ai/health")
async def assistant_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """System snapshot used by the Flutter assistant widget health check."""
    return {"status": "ok", "snapshot": _collect_system_snapshot(db)}
