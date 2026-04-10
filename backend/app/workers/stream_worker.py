import threading
import logging
import time
import numpy as np
import cv2
from datetime import timedelta
from typing import Dict
from app.db import SessionLocal
from app.config import settings
from app.ai.stream_manager import stream_manager
from app.ai.detector import Detector
from app.ai.tracker import Tracker
from app.ai.face_recognizer import FaceRecognizer
from app.ai.event_engine import EventEngine
from app.ai.attendance_engine import AttendanceEngine
from app.ai.clip_manager import ClipManager
from app.repositories.camera_repository import CameraRepository
from app.repositories.employee_repository import EmployeeRepository
from app.models.employee import EmployeeFaceTemplate
from app.models.tracking import PersonSighting, TrackEvent
from app.models.archive import ArchiveRecord

logger = logging.getLogger(__name__)


class StreamWorker:
    """
    Main background worker that runs the AI pipeline for all active cameras.
    """

    def __init__(self):
        self.detector = Detector(settings.DETECTOR_MODEL, device=settings.AI_DEVICE, tracker_type=settings.TRACKER_TYPE)
        self.tracker = Tracker(settings.TRACKER_TYPE)
        self.face_rec = FaceRecognizer(settings.FACE_MODEL_DIR, device=settings.AI_DEVICE)
        self.event_engine = EventEngine()
        self.clip_mgr = ClipManager()
        self._running = False
        self._threads: Dict[int, threading.Thread] = {}
        self._camera_stop_events: Dict[int, threading.Event] = {}
        self._last_snapshot_times = {}  # (camera_id, track_id) -> timestamp
        self._track_info: Dict[tuple, tuple] = {}  # (camera_id, track_id) -> (employee_id, confidence)
        self.latest_annotated_frames: Dict[int, tuple] = {}  # camera_id -> (timestamp, annotated_img)
        self._main_thread = None
        
        # --- Self-Understanding Telemetry (Trend 2026) ---
        self.telemetry = {
            "fps_real": {},  # cam_id -> float
            "latency_ms": {}, # cam_id -> float
            "detections_total": 0,
            "recognitions_total": 0
        }
        # -------------------------------------------------

    def start(self):
        if self._running:
            logger.warning("[Worker] StreamWorker is already running.")
            return
        
        self._running = True
        logger.info("[Worker] Starting StreamWorker thread...")
        
        # We start the main loop in its own thread so this method isn't blocking
        self._main_thread = threading.Thread(target=self._run_internal, daemon=True)
        self._main_thread.start()

    def _run_internal(self):
        """Internal execution thread to avoid blocking the caller."""
        # Load known faces into recognizer
        db = SessionLocal()
        try:
            templates = db.query(EmployeeFaceTemplate).all()
            
            employees_data = []
            for t in templates:
                employees_data.append({
                    "id": t.employee_id,
                    "face_image_path": t.image_path
                })
                
            if employees_data:
                logger.info(f"[Worker] Loading {len(employees_data)} face templates into gallery...")
                self.face_rec.load_gallery(employees_data)
        except Exception as e:
            logger.error(f"[Worker] Failed to load face templates: {e}")
        finally:
            db.close()

        # Start multi-camera processing
        self._main_loop()

    @property
    def is_running(self) -> bool:
        return self._running

    def stop(self):
        """Stop all AI processing threads and release video writers."""
        logger.info("[Worker] Manual stop initiated...")
        self._running = False
        
        # Stop all cameras in stream_manager to finalize mp4 files
        active_ids = list(self._threads.keys())
        for cam_id in active_ids:
            self.stop_camera(cam_id)
            
        logger.info("[Worker] Full stop complete.")

    def stop_camera(self, camera_id: int):
        """Stop processing for a specific camera."""
        if camera_id in self._camera_stop_events:
            logger.info(f"[Worker] Stopping individual camera {camera_id}...")
            self._camera_stop_events[camera_id].set()
            if camera_id in self._threads:
                self._threads[camera_id].join(timeout=1.0)
                self._threads.pop(camera_id, None)
            self._camera_stop_events.pop(camera_id, None)
            stream_manager.stop_camera(str(camera_id))

    def start_camera(self, camera_id: int):
        """Public interface for Watchdog to restart a camera thread."""
        with SessionLocal() as db:
            from app.models.camera import Camera
            cam = db.query(Camera).get(camera_id)
            if cam and cam.status == "online":
                # Ensure it's fully stopped first
                self.stop_camera(camera_id)
                stream_manager.add_camera(str(cam.id), cam.stream_url)
                
                stop_event = threading.Event()
                self._camera_stop_events[cam.id] = stop_event
                
                t = threading.Thread(
                    target=self._process_camera,
                    args=(cam.id, stop_event),
                    daemon=True,
                )
                t.start()
                self._threads[cam.id] = t
                logger.info(f"[Worker] Watchdog re-started camera thread {cam.id}")

    def _main_loop(self):
        """Monitor cameras and start/stop streams based on DB status."""
        while self._running:
            db = SessionLocal()
            try:
                cam_repo = CameraRepository(db)
                cameras = cam_repo.get_all()
                online_ids = [cam.id for cam in cameras if cam.status == "online"]

                # 1. Stop cameras that became offline or were removed
                active_ids = list(self._threads.keys())
                for cam_id in active_ids:
                    if cam_id not in online_ids:
                        self.stop_camera(int(cam_id))

                # 2. Start cameras up to MAX_ACTIVE_CAMERAS
                for cam in cameras:
                    # If camera is supposed to be online but not in self._threads
                    if cam.status == "online" and cam.id not in self._threads:
                        if len(self._threads) >= settings.MAX_ACTIVE_CAMERAS:
                            logger.warning(f"[Worker] Active camera limit reached ({settings.MAX_ACTIVE_CAMERAS}). Skipping camera {cam.id}")
                            continue

                        # Only add to manager and start thread if we are not already tracking it
                        # (Checking self._threads is enough because stop_camera cleans both)
                        stream_manager.add_camera(str(cam.id), cam.stream_url)

                        # Create stop event for this camera
                        stop_event = threading.Event()
                        self._camera_stop_events[cam.id] = stop_event

                        # Start processing thread for this camera
                        t = threading.Thread(
                            target=self._process_camera,
                            args=(cam.id, stop_event),
                            daemon=True,
                        )
                        t.start()
                        self._threads[cam.id] = t
                        logger.info(f"[Worker] Started processing thread for camera {cam.id}")

            except Exception as e:
                logger.error(f"[Worker] Main loop error: {e}")
            finally:
                db.close()
                time.sleep(5)  # Yield for 5 seconds between camera state checks to avoid CPU thrashing

            # Use small sleeps in loop to remain responsive to stop command
            for _ in range(100):
                if not self._running:
                    break
                time.sleep(0.1)  # Check for camera updates every 10s wait

    def _process_camera(self, camera_id: int, stop_event: threading.Event):
        """Individual camera processing loop."""
        logger.info(f"[Worker] Processing thread started for camera {camera_id}")

        frame_count = 0
        quiet_frames = 0
        current_skip = settings.GLOBAL_FRAME_SKIP

        last_processed_ts = None

        try:
            while self._running and not stop_event.is_set():
                # 1. Fetch latest frame from BACKGROUND AI QUEUE
                start_proc = time.time()
                frame_data = stream_manager.get_ai_frame(str(camera_id), timeout=0.1)
                if not frame_data:
                    time.sleep(0.01)
                    continue

                ts, img = frame_data
                if last_processed_ts == ts:
                    time.sleep(0.005) # Wait for a new frame
                    continue
                
                last_processed_ts = ts

                frame_count += 1
                if frame_count % current_skip != 0:
                    continue

                ts, img = frame_data
                img_np = np.array(img)

                # 2. Detect people
                detections = self.detector.detect(img_np, camera_id=camera_id)
                
                # Dynamic Throttling (Trend 2026)
                if not detections:
                    quiet_frames += 1
                    if quiet_frames > 50: # No one for ~50 processed frames
                        current_skip = min(settings.GLOBAL_FRAME_SKIP * 4, 15)
                else:
                    quiet_frames = 0
                    current_skip = settings.GLOBAL_FRAME_SKIP
                
                # Update Telemetry
                self.telemetry["detections_total"] += len(detections)

                # 3. Track persistence (already handled in detector.detect() with tracker integration)
                tracks = detections  # detections are already tracked via detector.detect()

                with SessionLocal() as db:
                    att_engine = AttendanceEngine(db)

                    for track in tracks:
                        track_id = track.get("track_id", 0)
                        box = track.get("box")
                        x1, y1, x2, y2 = map(int, box)

                        # --- Privacy Blur (Trend 2026) ---
                        if settings.ENABLE_PRIVACY_BLUR:
                            # Ensure coordinates are within image bounds
                            h, w = img_np.shape[:2]
                            ay1, ay2 = max(0, y1), min(h, y2)
                            ax1, ax2 = max(0, x1), min(w, x2)
                            
                            if ay2 > ay1 and ax2 > ax1:
                                roi = img_np[ay1:ay2, ax1:ax2]
                                # Apply heavy blur to mask identity in standard view
                                blurred_roi = cv2.GaussianBlur(roi, (51, 51), 0)
                                img_np[ay1:ay2, ax1:ax2] = blurred_roi
                        else:
                            # Ensure ay1, ax1 etc. are defined even if blur is off for anomaly capture
                            h, w = img_np.shape[:2]
                            ay1, ay2 = max(0, y1), min(h, y2)
                            ax1, ax2 = max(0, x1), min(w, x2)
                        # ---------------------------------

                        # 4. Selective Face Recognition
                        # Only run face rec if we don't have a reliable result for this track
                        employee_id = track.get("employee_id")
                        confidence = track.get("confidence", 0.0)

                        # Update track state if we already have high confidence
                        state_key = (camera_id, track_id)
                        if state_key in self._track_info:
                            cached_id, cached_conf = self._track_info[state_key]
                            if cached_conf >= 0.6:
                                employee_id = cached_id
                                confidence = cached_conf

                        # Heuristic: if track is new, unknown, or confidence was low
                        crop = None
                        if not employee_id or confidence < 0.6:
                            x1, y1, x2, y2 = map(int, box)
                            # Ensure coordinates are within image bounds
                            h, w = img_np.shape[:2]
                            y1, y2 = max(0, y1), min(h, y2)
                            x1, x2 = max(0, x1), min(w, x2)
                            
                            crop = img_np[y1:y2, x1:x2]
                            if crop is not None and crop.size > 0:
                                emb = self.face_rec.get_embedding(crop)
                                if emb is not None:
                                    new_id, new_conf = self.face_rec.match(emb)
                                    if new_id and new_conf > confidence:
                                        employee_id = new_id
                                        confidence = new_conf
                                        # Cache the reliable result
                                        self._track_info[state_key] = (employee_id, confidence)

                        # 5. Event Aggregation
                        self.event_engine.process_raw_track(
                            camera_id, track_id, employee_id, confidence
                        )

                        # 6. Immediate Attendance logging & Security Checks
                        if employee_id:
                            # Fetch the current track session to see if it's loitering
                            current_sess = self.event_engine.active_tracks.get(track_id)
                            event_type = "sighting"
                            if current_sess and current_sess.is_loitering:
                                event_type = "loitering_anomaly"

                            # Watchlist Check
                            from app.models.watchlist import Watchlist
                            is_watchlisted = db.query(Watchlist).filter(
                                Watchlist.employee_id == str(employee_id),
                                Watchlist.is_active == True
                            ).first()

                            if is_watchlisted:
                                event_type = "security_breach"
                                logger.warning(f"[SECURITY] Watchlist match for {employee_id} at cam {camera_id}")

                            # Record the frame event in DB for analytics
                            try:
                                ev = TrackEvent(
                                    camera_id=camera_id,
                                    track_id=track_id,
                                    confidence=float(confidence),
                                    timestamp=ts
                                )
                                db.add(ev)
                                att_engine.process_event(employee_id, ts, camera_id, event_type)
                            except Exception as e:
                                logger.error(f"[Worker] Failed to save track event: {e}")

                            # Log critical anomalies directly to Archive
                            if event_type in ["loitering_anomaly", "security_breach"]:
                                from datetime import timedelta
                                existing_anomaly = db.query(ArchiveRecord).filter(
                                    ArchiveRecord.camera_id == camera_id,
                                    ArchiveRecord.employee_id == employee_id,
                                    ArchiveRecord.event_type == event_type,
                                    ArchiveRecord.created_at >= ts - timedelta(minutes=5)
                                ).first()
                                
                                if not existing_anomaly:
                                    logger.info(f"[Worker] Persisting {event_type} for ID {employee_id}")
                                    img_to_save = crop if crop is not None else img_np[ay1:ay2, ax1:ax2]
                                    path = self._save_unknown_face(img_to_save, camera_id)
                                    title = f"Security Breach Detected: #{employee_id}" if event_type == "security_breach" else f"Loitering Detected: #{employee_id}"
                                    arc = ArchiveRecord(
                                        employee_id=employee_id,
                                        camera_id=camera_id,
                                        event_type=event_type,
                                        title=title,
                                        file_path=path,
                                    )
                                    db.add(arc)
                        else:
                            # Capture unknown face with cooldown
                            now = int(time.time())
                            if (
                                now
                                - self._last_snapshot_times.get((camera_id, track_id), 0)
                                >= settings.FACE_RECOGNITION_COOLDOWN_SECONDS
                            ):
                                img_to_save = crop if crop is not None else img_np[ay1:ay2, ax1:ax2]
                                if (
                                    img_to_save is not None
                                    and img_to_save.size > 0
                                    and img_to_save.shape[0] > 60
                                ):
                                    self._save_unknown_face(img_to_save, camera_id)
                                    self._last_snapshot_times[(camera_id, track_id)] = now

                    # Handle timed-out tracks (completed events)
                    completed = self.event_engine.get_completed_events()
                    for sess in completed:
                        try:
                            sighting = PersonSighting(
                                employee_id=sess.employee_id,
                                camera_id=camera_id,
                                track_id=sess.track_id,
                                first_seen=sess.first_seen,
                                last_seen=sess.last_seen,
                                duration_seconds=int((sess.last_seen - sess.first_seen).total_seconds()),
                                confidence_score=sess.confidence_sum / sess.match_count if sess.match_count > 0 else 0.0
                            )
                            db.add(sighting)
                        except Exception as e:
                            logger.error(f"[Worker] Failed to wrap PersonSighting: {e}")

                        # Cleanup cached track info
                        self._track_info.pop((camera_id, sess.track_id), None)

                    # Final commit for the frame's processing tasks
                    try:
                        db.commit()
                    except Exception as e:
                        logger.error(f"[Worker] DB Commit Failure for camera {camera_id}: {e}")
                        db.rollback()

                # --- Draw Annotations ---
                annotated_img = img_np.copy()
                for track in tracks:
                    track_id = track.get("track_id", 0)
                    box = track.get("box")
                    x1, y1, x2, y2 = map(int, box)
                    
                    state_key = (camera_id, track_id)
                    label = f"ID: {track_id}"
                    color = (0, 0, 255) # Red for unknown
                    if state_key in self._track_info:
                        emp_id, conf = self._track_info[state_key]
                        if emp_id:
                            label = f"Emp {emp_id} ({conf:.2f})"
                            color = (0, 255, 0) # Green for known
                            
                    cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(annotated_img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                self.latest_annotated_frames[camera_id] = (ts, annotated_img)
                
                # --- Update End-of-Frame Telemetry ---
                duration = (time.time() - start_proc) * 1000
                self.telemetry["latency_ms"][camera_id] = duration
                # Simple FPS estimate based on inter-processing duration
                if duration > 0:
                    self.telemetry["fps_real"][camera_id] = 1000.0 / duration
                # --------------------------------------

        except Exception as e:
            logger.error(f"[Worker] Camera worker {camera_id} error: {e}")

    def _save_unknown_face(self, crop, camera_id):
        import os
        import cv2
        import time

        os.makedirs(settings.CAPTURED_FACES_DIR, exist_ok=True)
        # Limit folder size by checking count or just using time
        # For production: use a deque or cleanup task
        filename = f"unknown_{camera_id}_{int(time.time() * 1000)}.jpg"
        path = os.path.join(settings.CAPTURED_FACES_DIR, filename)

        # Save BGR image (detector/tracker usually provide BGR or we convert)
        # Assuming crop is BGR (OpenCV standard)
        cv2.imwrite(path, crop)
        return path


# Singleton instance
stream_worker = StreamWorker()
