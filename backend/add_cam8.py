import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.db import SessionLocal
from app.models.camera import Camera

db = SessionLocal()
cam8 = db.query(Camera).filter(Camera.id == 8).first()
if not cam8:
    cam8 = Camera(id=8, name="Web Camera 8", location="Webcam", channel_no=8, stream_url="0", status="online")
    db.add(cam8)
else:
    cam8.stream_url = "0"
    cam8.name = "Web Camera 8"
    cam8.status = "online"
db.commit()
print("Camera 8 added/updated!")
