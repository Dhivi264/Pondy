import os
import time
import logging
import cv2
import threading
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional

from app.db import SessionLocal
from app.config import settings
from app.models.batch_job import ProcessingJob
from app.models.tracking import PersonSighting
from app.models.camera import Camera
from app.ai.detector import Detector
from app.ai.face_recognizer import FaceRecognizer
from app.models.employee import EmployeeFaceTemplate

logger = logging.getLogger("BatchProcessor")

class BatchVideoProcessor:
    def __init__(self, watch_folder: str):
        self.watch_folder = watch_folder
        self.running = False
        self._thread = None
        
        # We load these lazily to avoid heavy startup if not processing
        self.detector = None
        self.face_rec = None
        self.gallery_loaded = False
        
        os.makedirs(self.watch_folder, exist_ok=True)

    def _init_models(self):
        if not self.detector:
            self.detector = Detector(settings.DETECTOR_MODEL, device=settings.AI_DEVICE)
        if not self.face_rec:
            self.face_rec = FaceRecognizer(settings.FACE_MODEL_DIR, device=settings.AI_DEVICE)
            with SessionLocal() as db:
                templates = db.query(EmployeeFaceTemplate).all()
                self.face_rec.load_gallery([{"id": t.employee_id, "face_image_path": t.image_path} for t in templates])
            self.gallery_loaded = True

    def start(self):
        if self.running: return
        self.running = True
        self._thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self._thread.start()
        logger.info(f"[BatchEngine] Started monitoring folder: {self.watch_folder}")

    def stop(self):
        self.running = False

    def _extract_camera_name(self, filename: str) -> str:
        """
        EXAMPLE: CAM_FRONTGATE_2026.mp4 -> Front Gate Camera
        If it finds a standard formatting, it extracts it, otherwise defaults to UNKNOWN.
        """
        fn_upper = filename.upper()
        if fn_upper.startswith("CAM_"):
            parts = fn_upper.split("_")
            if len(parts) > 1:
                return f"{parts[1].capitalize()} Camera"
        return "Unknown Batch Camera"

    def _watcher_loop(self):
        """1. FOOTAGE FOLDER MONITORING (Thread/Process queue for footage)"""
        while self.running:
            try:
                self._scan_folder_for_jobs()
                self._process_next_job()
            except Exception as e:
                logger.error(f"[BatchEngine] Watcher loop error: {e}")
            time.sleep(10)  # Check every 10s

    def _scan_folder_for_jobs(self):
        exts = ('.mp4', '.avi', '.mkv')
        files = [f for f in os.listdir(self.watch_folder) if f.lower().endswith(exts)]
        db = SessionLocal()
        try:
            for file in files:
                # Avoid duplicate insertion
                job = db.query(ProcessingJob).filter_by(filename=file).first()
                if not job:
                    cam_name = self._extract_camera_name(file)
                    new_job = ProcessingJob(
                        filename=file,
                        file_path=os.path.join(self.watch_folder, file),
                        camera_name=cam_name,
                        status="pending"
                    )
                    db.add(new_job)
                    logger.info(f"[BatchEngine] File discovered: {file} (Camera: {cam_name})")
            db.commit()
        finally:
            db.close()

    def _process_next_job(self):
        db = SessionLocal()
        try:
            job = db.query(ProcessingJob).filter_by(status="pending").first()
            if not job:
                return

            # Mark as processing
            job.status = "processing"
            job.started_at = datetime.utcnow()
            db.commit()

            # Ensure models are loaded
            self._init_models()

            logger.info(f"[BatchEngine] Video opened successfully: {job.filename}")
            success, err_msg = self._process_video(job.file_path, job.camera_name, db)
            
            # End state
            if success:
                job.status = "completed"
                logger.info(f"[BatchEngine] Processing completed: {job.filename}")
            else:
                job.status = "failed"
                job.error_log = err_msg
                logger.error(f"[BatchEngine] Processing failed with reason: {err_msg} for {job.filename}")
            
            job.completed_at = datetime.utcnow()
            db.commit()
            
        finally:
            db.close()

    def _process_video(self, file_path: str, camera_name: str, db: Session) -> tuple[bool, str]:
        """2. VIDEO PROCESSING PIPELINE"""
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return False, "Failed to open video. Corrupt or unsupported codec."
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_idx = 0
        skip_rate = int(fps) # Sample ~ 1 frame per second
        
        logger.info(f"[BatchEngine] Frame sampling started. Sampling 1 frame per {skip_rate} frames.")
        
        # Fetch or mock a generic camera ID for sightings
        target_cam = db.query(Camera).filter(Camera.name.ilike(f"%{camera_name}%")).first()
        cam_id = target_cam.id if target_cam else 9999
        
        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_idx += 1
                if frame_idx % skip_rate != 0:
                    continue  # Do NOT process every frame unless necessary
                    
                # 3. FACE / PERSON DETECTION
                detections = self.detector.detect(frame)
                if not detections:
                    continue # if no person/face, skip frame
                
                timestamp_sec = frame_idx / fps
                
                for det in detections:
                    if det.get("confidence", 1.0) < settings.FACE_MATCH_THRESHOLD:
                        continue # configurable confidence
                        
                    x1, y1, x2, y2 = map(int, det["box"])
                    crop = frame[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]
                    
                    if crop.size == 0: continue
                    
                    # 4. FACE RECOGNITION
                    emb = self.face_rec.get_embedding(crop)
                    if emb is None: continue
                    
                    emp_id, conf = self.face_rec.match(emb)
                    if emp_id:
                        logger.info(f"[BatchEngine] Face matched! Identity: {emp_id} (Conf: {conf:.2f})")
                        
                        # 5. EVENT / SIGHTING STORAGE
                        db_sighting = PersonSighting(
                            employee_id=emp_id,
                            camera_id=cam_id, 
                            first_seen=datetime.fromtimestamp(timestamp_sec), # Storing as relative offset for test
                            last_seen=datetime.fromtimestamp(timestamp_sec),
                            confidence_score=conf,
                            duration_seconds=0
                        )
                        db.add(db_sighting)
                        try:
                            db.commit()
                            logger.info(f"[BatchEngine] DB insert success: Logged sighting for worker {emp_id}")
                        except IntegrityError:
                            db.rollback()
                            logger.error("[BatchEngine] DB insert failure: Integrity Error")
                    else:
                        logger.debug("[BatchEngine] Face detected but identity UNKNOWN")
                        
            return True, ""
        except Exception as e:
            logger.error(f"[BatchEngine] Unhandled error during video execution: {e}")
            return False, str(e)
        finally:
            cap.release()

batch_engine = BatchVideoProcessor(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "videos"))
