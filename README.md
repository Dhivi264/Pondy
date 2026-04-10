# Smart CCTV Analytics Platform

A unified AI surveillance platform bringing together edge AI processing, face recognition, and real-time frontend monitoring.

## 🏗 System Architecture 

Built on a modern micro-services architecture to allow resilient real-time processing:
- **Frontend App**: Flutter & Riverpod
- **Backend API**: Python, FastAPI, and Uvicorn
- **AI Core**: YOLOv11 & MobileNet/HOG Face Embedding Engine
- **Database Backend**: Microsoft Access `.accdb` (Supports SQLAlchemy migration to SQL Server)

## 🚀 Quickstart

### 1. Initialize Backend
```powershell
cd backend/
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python run.py
```
*Your backend will initialize local OpenCV video streams, load neural models, establish database seeds, and expose the FastAPI router at http://0.0.0.0:8000.*

### 2. Launch Client Interface
```powershell
# From the project root
flutter pub get
flutter run -d windows
```

## 🔥 Core Capabilities

- **Adaptive Edge Skip-Processing:** Automatically detects hardware (Intel NCS, Jetson Nano, CUDA Server) to configure frame-skip ratios and avoid processing latency. 
- **YOLOv11 Person Tracking & Fall-back Identification:** Utilizes MobileNet/HOG fallback models for 128-d face embedding even when `insightface` isn't supported on particular hardware profiles.
- **Background Stream Workers:** Spawns asynchronous Python threads polling the RTSP/local endpoints independent of UI lag.
- **Smart Event Cleanup:** Prevents memory leaks by continuously flushing localized tracking coordinates from memory state matrices.
