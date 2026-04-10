import os
import cv2
import time
import logging
import numpy as np
from app.db import SessionLocal
from app.config import settings
from app.ai.detector import Detector
from app.ai.face_recognizer import FaceRecognizer
from app.models.employee import EmployeeFaceTemplate
from app.models.tracking import PersonSighting

# STEP 9: ADD LOGGING
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("VideoProcessor")

def run_offline_processing(video_folder: str):
    logger.info("================================================")
    logger.info("STEP 1 - VERIFY INPUT PIPELINE")
    
    if not os.path.exists(video_folder):
        logger.error(f"Folder not found: {video_folder}")
        return
        
    exts = ('.mp4', '.avi', '.mkv')
    files = [f for f in os.listdir(video_folder) if f.lower().endswith(exts)]
    
    if not files:
        logger.warning("System is skipping files silently or no valid videos found.")
        return
        
    logger.info(f"Detected {len(files)} files: {files}")

    logger.info("STEP 4 - VERIFY MODEL LOADING")
    try:
        detector = Detector(settings.DETECTOR_MODEL, device=settings.AI_DEVICE)
        face_rec = FaceRecognizer(settings.FACE_MODEL_DIR, device=settings.AI_DEVICE)
        logger.info("Model initialization success")
    except Exception as e:
        logger.error(f"Model not loading: {e}")
        return

    logger.info("STEP 6 - VERIFY FACE RECOGNITION (Load Gallery)")
    db = SessionLocal()
    try:
        templates = db.query(EmployeeFaceTemplate).all()
        if not templates:
            logger.warning("No face embeddings found in known persons database.")
        else:
            gal = [{"id": t.employee_id, "face_image_path": t.image_path} for t in templates]
            face_rec.load_gallery(gal)
            logger.info("Embeddings exist and match format.")
    except Exception as e:
        logger.error(f"Gallery load issue: {e}")
    finally:
        db.close()

    for idx, filename in enumerate(files):
        logger.info(f"\n--- Processing Video {idx+1}/{len(files)}: {filename} ---")
        file_path = os.path.join(video_folder, filename)
        
        # STEP 2 - VERIFY VIDEO READING
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            logger.error(f"Failed to open video. Check codec issue or file corruption. Suggest FFmpeg fallback.")
            continue
            
        ret, frame = cap.read()
        if not ret or frame is None:
            logger.error("Failed to read first frame. Video opened but returns Empty.")
            continue
        logger.info("Video opened successfully. First frame read.")

        # Reset for loop
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        # STEP 8 - VERIFY JOB FLOW
        logger.info(f"Job Status: pending -> processing ({filename})")
        
        frame_idx = 0
        skip_rate = 5  # Step 3 logic
        
        db = SessionLocal()
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                frame_idx += 1
                
                # STEP 3 - VERIFY FRAME SAMPLING
                if frame_idx % skip_rate != 0:
                    continue
                
                timestamp = frame_idx / cap.get(cv2.CAP_PROP_FPS)
                logger.info(f"Frame extracted: index {frame_idx}, timestamp {timestamp:.2f}s")
                
                # STEP 5 - VERIFY DETECTION PIPELINE
                detections = detector.detect(frame)
                if not detections:
                    logger.debug("Detection returns empty bounding boxes.")
                    continue
                    
                logger.info(f"Detection result: {len(detections)} persons found")
                
                for det in detections:
                    x1, y1, x2, y2 = map(int, det["box"])
                    crop = frame[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]
                    
                    if crop.size == 0:
                        continue
                        
                    emb = face_rec.get_embedding(crop)
                    if emb is None:
                        continue
                        
                    # STEP 6 - Compare detected faces
                    emp_id, conf = face_rec.match(emb)
                    if not emp_id:
                        logger.info("Recognition mismatch: Unknown person.")
                        continue
                        
                    logger.info(f"Recognition result: Matched Employee #{emp_id} (Confidence: {conf:.2f})")
                    
                    if conf > 0.6:
                        # STEP 7 - VERIFY DATABASE WRITE
                        logger.info(f"DB Insert Query: PersonSighting(employee_id={emp_id}, frame_index={frame_idx})")
                        sighting = PersonSighting(
                            employee_id=emp_id,
                            camera_id=999, # Dummy offline processing ID
                            first_seen=time.strftime('%Y-%m-%d %H:%M:%S'),
                            duration_seconds=0,
                            confidence_score=conf
                        )
                        db.add(sighting)
            
            # STEP 7 / 8 Commit Flow
            db.commit()
            logger.info("DB commit successful. Data actually written.")
            logger.info(f"Job Status: processing -> completed ({filename})")
            
        except Exception as e:
            logger.error(f"Job failed with error: loop crashed silently. Exception: {e}")
            db.rollback()
        finally:
            cap.release()
            db.close()

if __name__ == "__main__":
    run_offline_processing(os.path.join(os.path.dirname(__file__), "videos"))
