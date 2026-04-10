import sys
import os
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models.camera import Camera
import socket
from urllib.parse import urlparse

def check_cameras():
    db = SessionLocal()
    try:
        cameras = db.query(Camera).all()
        print(f"Found {len(cameras)} cameras in database.")
        for cam in cameras:
            print(f"ID: {cam.id}, Name: {cam.name}, Status: {cam.status}, URL: {cam.stream_url}")
            if cam.stream_url:
                parsed = urlparse(cam.stream_url)
                host = parsed.hostname
                port = parsed.port or (554 if parsed.scheme == 'rtsp' else 80)
                if host:
                    try:
                        print(f"  Attempting TCP connection to {host}:{port}...")
                        with socket.create_connection((host, port), timeout=2.0):
                            print(f"  [SUCCESS] {host}:{port} is reachable.")
                    except Exception as e:
                        print(f"  [FAILURE] {host}:{port} is NOT reachable: {e}")
                else:
                    print(f"  [ERROR] Could not parse host from URL: {cam.stream_url}")
    finally:
        db.close()

if __name__ == "__main__":
    # Add project root to sys.path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(project_root)
    check_cameras()
