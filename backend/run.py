import uvicorn
import logging
import sys
import os

# Ensure the backend directory is in the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import SessionLocal, engine, Base
from app.models.user import User
from app.auth import get_password_hash

logging.basicConfig(level=logging.INFO)

from app.models.camera import Camera


def seed_camera():
    """Webcam seeding disabled as per request."""
    print("[Seed] Webcam seeding disabled - no webcam will be added")
    return


def seed_admin():
    """Ensure a default admin user exists."""
    # Create tables first
    print("[DB] Initializing tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            print("[Seed] Creating default admin user...")
            admin = User(
                username="admin",
                full_name="System Administrator",
                password_hash=get_password_hash("admin123"),
                role="admin",
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


def run_migrations():
    """Ensure SQLite schema is up to date with newest features (AI Anomaly Analytics)."""
    import sqlite3

    db_file = "production.db"
    if not os.path.exists(db_file):
        return

    print("[DB] Checking for required schema updates...")
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # 1. Check for loitering_flag in attendance_sessions
        cursor.execute("PRAGMA table_info(attendance_sessions)")
        columns = [row[1] for row in cursor.fetchall()]

        updates = [
            ("loitering_flag", "INTEGER DEFAULT 0"),
            ("last_anomaly_detected", "DATETIME"),
            ("total_suspicious_duration", "INTEGER DEFAULT 0"),
        ]

        for col_name, col_type in updates:
            if col_name not in columns:
                print(
                    f"[DB] Adding missing column '{col_name}' to attendance_sessions..."
                )
                cursor.execute(
                    f"ALTER TABLE attendance_sessions ADD COLUMN {col_name} {col_type}"
                )

        conn.commit()
        conn.close()
        print("[DB] Schema verification complete.")
    except Exception as e:
        print(f"[DB] Migration notice: {e}")


def seed_video_folder():
    """Scan 'videos' directory and add all video files as camera streams."""
    video_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
    if not os.path.exists(video_dir):
        print(f"[Seed] Skipping video folder scan (not found: {video_dir})")
        return

    print(f"[Seed] Scanning for video archives in {video_dir}...")
    db = SessionLocal()
    try:
        exts = (".mp4", ".avi", ".mkv", ".mov")
        files = [f for f in os.listdir(video_dir) if f.lower().endswith(exts)]

        for idx, f in enumerate(files):
            full_path = os.path.abspath(os.path.join(video_dir, f))
            # Check if exists
            exists = db.query(Camera).filter(Camera.stream_url == full_path).first()
            if not exists:
                print(f"[Seed] Auto-registering video stream: {f}")
                cam = Camera(
                    name=f"Archive Stream {idx + 1}: {f[:8]}",
                    stream_url=full_path,
                    location="Simulated Zone",
                    status="online",
                    is_entry_camera=False,
                )
                db.add(cam)
        db.commit()
    except Exception as e:
        print(f"[Seed] Failed to register video archives: {e}")
    finally:
        db.close()


def kill_port_8000():
    """Kill any process running on port 8000 to avoid 'address already in use' errors."""
    import psutil
    import subprocess

    print("[Server] Checking for previous backend instances on port 8000...")
    try:
        # Cross-platform way to find and kill process on port 8000
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                for conns in proc.net_connections(kind="inet"):
                    if conns.laddr.port == 8000:
                        print(
                            f"[Server] Killing orphaned process {proc.info['name']} (PID: {proc.info['pid']}) on port 8000..."
                        )
                        proc.terminate()
                        proc.wait(timeout=3)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        # Fallback to shell command on Windows
        if sys.platform == "win32":
            try:
                subprocess.run(
                    'powershell -Command "Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force -ErrorAction SilentlyContinue"',
                    shell=True,
                )
            except:
                pass


if __name__ == "__main__":
    # 0. Clean up environment
    kill_port_8000()

    # 1. Initialize DB seeds & Migrations
    run_migrations()
    seed_admin()
    seed_camera()
    seed_video_folder()

    # 1.5 Find local IP addresses for connectivity convenience
    import socket

    hostname = socket.gethostname()
    local_ips = [socket.gethostbyname(hostname)]
    # Try to find more if possible (optional)
    try:
        local_ips += [
            ip[4][0] for ip in socket.getaddrinfo(hostname, None) if ":" not in ip[4][0]
        ]
    except:
        pass
    local_ips = list(set(local_ips))

    print(f"\n[Server] Listening on 0.0.0.0:8000")
    print(f"[Server] Accessible locally via: http://localhost:8000")
    for ip in local_ips:
        if ip != "127.0.0.1":
            print(f"[Server] Accessible on network via: http://{ip}:8000")
    print("")

    # 2. Run API server (Persistence Loop: Trend 2026)
    port = int(os.environ.get("PORT", 8000))
    print(f"[Server] Starting FastAPI on port {port}...")
    while True:
        try:
            uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
        except Exception as e:
            print(f"[Server] Restarting due to error: {e}")
            import time

            time.sleep(2)
        except SystemExit:
            print("[Server] SystemExit received. Restarting persistent listener...")
            import time

            time.sleep(2)
