from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import engine, Base

# Import all models to register them with Base
import app.models.user
import app.models.camera
import app.models.employee
import app.models.attendance
import app.models.tracking
import app.models.settings
import app.models.archive
import app.models.package
import app.models.batch_job  # Added for Batch AI Job tracking
import app.models.notifications  # Added for Health Monitoring & Notifications
import app.models.watchlist  # Added for Security Watchlists

# Create DB tables
Base.metadata.create_all(bind=engine)

from app.routers import (
    auth_router,
    dashboard_router,
    employee_router,
    camera_router,
    attendance_router,
    integration_router,
    analytics_router,
    notifications_router,  # Added Notifications Router
    ai_monitoring_router,  # Added Comprehensive AI Monitoring Router
)
from app.routers import ai_assistant_router

import os
from app.workers.stream_worker import stream_worker
from app.workers.health_check_worker import health_check_worker  # Added Health Check Worker
from app.workers.storage_worker import storage_worker  # Added Storage Worker
from app.ai.batch_processor import batch_engine  # Added Batch Worker
import threading

app = FastAPI(
    title=settings.APP_NAME,
    version="3.0.0",
    description="Production-grade Smart CCTV Backend with AI Lifecycle and Dual DB Architecture.",
)

@app.on_event("startup")
async def startup_event():
    # 1. Ensure directories exist
    os.makedirs(settings.RECORDINGS_DIR, exist_ok=True)
    os.makedirs(settings.FACES_DIR, exist_ok=True)

    # 2. Start AI Pipeline & Self-Repair Watchdog
    from app.ai.watchdog import watchdog
    stream_worker.start()
    watchdog.start()

    # 3. Start Health Check Worker (scans every 10 minutes)
    health_check_worker.start()

    # 3.5 Start Storage Maintenance Worker (cleans old recordings automatically)
    storage_worker.start()

    # 4. Start Offline Batch Processing Monitoring
    batch_engine.start()


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
# Authentication
app.include_router(auth_router.router, prefix="/lmp/auth")
app.include_router(auth_router.router, prefix="/auth")

# Dashboard & Analytics
app.include_router(dashboard_router.router, prefix="/lmp")
app.include_router(dashboard_router.router)  # Top-level /dashboard, /anomalies etc.

# Employees
app.include_router(employee_router.router, prefix="/lmp/employees")
app.include_router(employee_router.router, prefix="/employees")

# Cameras
app.include_router(camera_router.router, prefix="/lmp/cameras")
app.include_router(camera_router.router, prefix="/cameras")

# Attendance
app.include_router(attendance_router.router, prefix="/lmp/attendance")
app.include_router(attendance_router.router, prefix="/attendance")

# Integration
app.include_router(integration_router.router, prefix="/lmp/integrations")

# AI Assistant
app.include_router(ai_assistant_router.router, prefix="/lmp")
app.include_router(ai_assistant_router.router)  # also at /ai/ask (no prefix)

# Search & Analytics
app.include_router(analytics_router.router, prefix="/analytics")
app.include_router(analytics_router.router)  # /search, /logs (no prefix)

# Batch Job APIs
from app.routers import batch_router
app.include_router(batch_router.router)

# Training APIs
from app.routers import training_router
app.include_router(training_router.router, prefix="/api/training", tags=["training"])

# Notifications & Health Monitoring
app.include_router(notifications_router.router, prefix="/lmp")
app.include_router(notifications_router.router)  # also at top-level

# AI System Monitoring & Control (Watchdog, Detector, Fusion, etc.)
app.include_router(ai_monitoring_router.router, prefix="/lmp")
app.include_router(ai_monitoring_router.router)  # also at top-level /ai endpoints

from fastapi.staticfiles import StaticFiles

# Serve media files
if not os.path.exists(settings.FACES_DIR):
    os.makedirs(settings.FACES_DIR)
if not os.path.exists(settings.CAPTURED_FACES_DIR):
    os.makedirs(settings.CAPTURED_FACES_DIR)
if not os.path.exists(settings.RECORDINGS_DIR):
    os.makedirs(settings.RECORDINGS_DIR)

app.mount("/faces", StaticFiles(directory=settings.FACES_DIR), name="faces")
app.mount(
    "/captured_faces",
    StaticFiles(directory=settings.CAPTURED_FACES_DIR),
    name="captured_faces",
)
app.mount(
    "/recordings",
    StaticFiles(directory=settings.RECORDINGS_DIR),
    name="recordings",
)


@app.get("/")
@app.get("/health")
@app.get("/ping")
def health_check():
    return {
        "status": "ok",
        "backend": "online",
        "message": "Smart CCTV Production Backend Running",
    }


from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    from app.ai.watchdog import watchdog
    error_type = type(exc).__name__
    error_detail = str(exc)

    # Delegate to the autonomous AI Watchdog
    watchdog.add_error(error_type, error_detail)

    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error intercepted by Self-Healing Watchdog", "details": error_detail}
    )



@app.post("/lmp/system/shutdown")
def shutdown_backend():
    import os
    import signal
    import threading
    import time
    from app.workers.stream_worker import stream_worker
    from app.workers.storage_worker import storage_worker

    def kill_server():
        time.sleep(1)
        # Gracefully stop worker threads
        stream_worker.stop()
        storage_worker.stop()
        # Kill the FastAPI process
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=kill_server, daemon=True).start()
    return {"message": "Shutting down..."}
