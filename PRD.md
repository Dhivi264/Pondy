# Product Requirements Document (PRD): Smart CCTV AI Application

## 1. Executive Summary
The Smart CCTV AI Application is a comprehensive mobile and backend system designed to ingest live network camera feeds, reliably record footage to local storage in manageable continuous chunks, and simultaneously process the fast-moving video feed through an AI pipeline (such as YOLOv11 and facial recognition models) for advanced analytics like face and person detection. 

## 2. Objectives
- **Centralized Surveillance:** To connect multiple RTSP/IP cameras or local webcams into a single dashboard.
- **Fail-Safe Archiving:** To automatically record and save camera footage continuously into a local storage folder (in 5-minute chunks).
- **Proactive Intelligence:** To run high-performance AI models concurrently on the ingested frames, targeting object tracking and face detection without lagging the live stream.
- **System Health Assurance:** To autonomously monitor the connection status and framerate health of all configured cameras, auto-healing or alerting administrators to any anomalies.

## 3. Core Workflow and Features

### 3.1. Camera Connection & Ingestion
- **Live Feed Connectivity**: Support for network IP cameras via standard streaming protocols (e.g., RTSP) utilizing TCP for reliable multi-camera ingestion.
- **Dynamic Camera Configuration**: Administrators can add, remove, or modify streaming sources through the front-end application.
- **Dual Pipeline Architecture**: The ingested stream is immediately duplicated into two queues:
  1. **Fast-Route Pipeline**: Proxies the lowest latency MJPEG stream to the Flutter frontend for user viewing.
  2. **AI-Route Pipeline**: Passes scaled/normalized frames to the background queue for object/face detection.

### 3.2. Continuous Automated Local Recording & Storage Maintenance
- **Background Archiving**: The system hooks into every active camera feed to capture footage non-intrusively using standardized H.264 (`avc1`) encoding.
- **Smart Chunking**: Video data is saved in sequential chunks (e.g., 300 seconds / 5 minutes) in `.mp4` format directly to `data/recordings`.
- **Predictive Storage Maintenance**: A background `storage_worker` constantly monitors the hard drive capacity. If usage exceeds 85%, the system automatically and permanently deletes the absolute oldest `.mp4` archives to prevent system crashes.

### 3.3. AI Processing Pipeline (Face/Object Detection)
- **Object Detection via YOLO**: Frames distributed to the AI queue undergo detection using the YOLOv11 model (person, objects, vehicles).
- **Face Detection and Recognition**: Secondary logic to crop out and identify unique faces or unknown persons.
- **Security Watchlists**: The AI actively dynamically checks generated Face IDs against a centralized database Watchlist, bypassing normal attendance and generating `security_breach` flags on positive hits.
- **Asynchronous Execution**: AI inference runs on separate threads, automatically dropping outdated frames if the queue becomes too backed up, preserving the integrity and timeline of the live view.

### 3.4. Auto-Healing & Notification System
- **Health Workers**: Background daemons scan camera statuses every 10 minutes.
- **Anomaly Detection**: Pattern tracking (offline limits, FPS drops) with machine learning logic to compute "confidence failure scores".
- **Self-Healing Actions**: System automatically resets buffering configurations or reduces frame limits if a camera appears unstable.
- **Push Notification Engine**: Upon critical, unrecoverable TCP disconnections, an asynchronous SMTP email dispatch alerts the system Administrator with error specifics and troubleshooting guidance.

## 4. Technical Architecture

### 4.1. Backend (Python/FastAPI)
- **Web Server**: FastAPI handles REST APIs and MJPEG streaming endpoints.
- **Stream Decoding Engine**: `PyAV` (FFmpeg underlying) provides high-performance TCP-backed decoding of RTSP feeds. `OpenCV` writes the frames sequentially to disk.
- **Concurrency**: `threading` and thread-safe Python `queue.Queue` are utilized for managing camera loops.
- **Database**: SQLite3 (`db.sqlite3` / `production.db`) handles metadata for cameras, users, logs, watchlists, notifications, and AI detection events.
- **AI Models**: Pytorch/YOLOv11 (`yolo11n.pt` / `yolo11s.pt`) serve as the foundation of the computer vision logic.

### 4.2. Frontend (Flutter)
- **Cross-Platform Mobile App**: Written in Dart utilizing Flutter, providing a reactive interface to consume REST endpoints.
- **Features**: Dashboard summaries, specific Camera Health details, Archive playback references, and real-time Notification viewing.

## 5. Non-Functional Requirements
- **Performance**: The backend must process at least 15-30 FPS per camera depending on AI computation resources.
- **Scalability**: Capable of dynamically scaling ingestion up to multiple cameras, restricted only by server hardware (CPU/GPU) limits.
- **Reliability**: Dual-pipeline strategy prevents stream-view crashes even when AI processing is overloaded. Fully protects itself against out-of-storage panics.
