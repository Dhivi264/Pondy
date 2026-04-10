from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth import get_current_user
from app.repositories.camera_repository import CameraRepository
from app.schemas import CameraResponse, CameraBase
from app.models.user import User

router = APIRouter(tags=["Cameras"])


@router.get("/", response_model=List[CameraResponse])
async def list_cameras(db: Session = Depends(get_db)):
    repo = CameraRepository(db)
    cameras = repo.get_all()
    results = []
    for cam in cameras:
        public_path = f"/lmp/cameras/{cam.id}/stream"
        results.append(CameraResponse(
            id=cam.id,
            name=cam.name,
            stream_url=public_path,
            public_url=public_path,
            location=cam.location or "Unknown",
            status=cam.status or "offline",
            is_entry_camera=cam.is_entry_camera,
            is_exit_camera=cam.is_exit_camera,
            fps=cam.frame_rate or 15,
            channel=cam.channel_no or 1,
            is_ai_active=(cam.status == "online"),
            created_at=cam.created_at,
        ))
    return results


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: int, db: Session = Depends(get_db)):
    repo = CameraRepository(db)
    cam = repo.get_by_id(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    public_path = f"/lmp/cameras/{cam.id}/stream"
    return CameraResponse(
        id=cam.id,
        name=cam.name,
        stream_url=public_path,
        public_url=public_path,
        location=cam.location or "Unknown",
        status=cam.status or "offline",
        is_entry_camera=cam.is_entry_camera,
        is_exit_camera=cam.is_exit_camera,
        fps=cam.frame_rate or 15,
        channel=cam.channel_no or 1,
        is_ai_active=(cam.status == "online"),
        created_at=cam.created_at,
    )


@router.get("/{camera_id}/stream")
async def stream_camera(camera_id: int, db: Session = Depends(get_db)):
    from fastapi.responses import StreamingResponse
    from app.ai.stream_manager import stream_manager
    import cv2
    import numpy as np

    import asyncio

    async def generate_frames():
        last_ts = None
        while True:
            # Always fallback to raw frame from stream_manager
            frame_data = stream_manager.get_frame(str(camera_id), timeout=1.0)
            if frame_data:
                ts, img = frame_data
                if ts == last_ts:
                    await asyncio.sleep(0.02)
                    continue
                last_ts = ts

                if img is not None:
                    # img can be PIL Image or numpy array
                    if hasattr(img, 'tobytes'):  # PIL Image
                        frame_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    else:  # numpy array (from webcam)
                        frame_np = cv2.cvtColor(img, cv2.COLOR_RGB2BGR) if len(img.shape) == 3 else img
                    ret, buffer = cv2.imencode(".jpg", frame_np, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if ret:
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                        )
                else:
                    await asyncio.sleep(0.05)
            else:
                await asyncio.sleep(0.05)

    return StreamingResponse(
        generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.post("/", response_model=CameraResponse)
async def create_camera(
    camera: CameraBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.config import settings
    repo = CameraRepository(db)
    
    # Check registration limit
    total_count = len(repo.get_all())
    if total_count >= settings.MAX_TOTAL_CAMERAS:
        raise HTTPException(
            status_code=400, 
            detail=f"Camera limit reached ({settings.MAX_TOTAL_CAMERAS}). Delete existing cameras first."
        )

    from app.models.camera import Camera
    return repo.create(Camera(**camera.dict()))

@router.post("/system/stop_ai")
async def stop_ai_pipeline(current_user: User = Depends(get_current_user)):
    """Manually stop all AI processing threads."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.workers.stream_worker import stream_worker
    stream_worker.stop()
    return {"status": "stopped", "message": "Global AI processing pipeline stopped."}

@router.post("/system/start_ai")
async def start_ai_pipeline(current_user: User = Depends(get_current_user)):
    """Manually start/restart AI processing threads."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.workers.stream_worker import stream_worker
    stream_worker.start()
    return {"status": "started", "message": "Global AI processing pipeline started."}

@router.get("/system/status_ai")
async def get_ai_status():
    """Check if AI pipeline is running."""
    from app.workers.stream_worker import stream_worker
    return {"is_running": stream_worker.is_running}

@router.post("/{camera_id}/stop_ai")
async def stop_camera_ai(camera_id: int, current_user: User = Depends(get_current_user)):
    """Manually stop AI processing for a specific camera thread."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.workers.stream_worker import stream_worker
    stream_worker.stop_camera(camera_id)
    return {"status": "stopped", "message": f"AI processing for camera {camera_id} stopped."}


@router.delete("/{camera_id}")
async def delete_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a camera and stop its processing thread."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    from app.workers.stream_worker import stream_worker
    repo = CameraRepository(db)
    
    # 1. Stop AI processing first
    stream_worker.stop_camera(camera_id)
    
    # 2. Delete from DB
    success = repo.delete(camera_id)
    if not success:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    return {"status": "success", "message": f"Camera {camera_id} deleted."}
