from app.db import SessionLocal
from app.models.camera import Camera


def add_local_webcam():
    db = SessionLocal()
    try:
        cam = db.query(Camera).filter(Camera.id == 8).first()
        if cam:
            cam.stream_url = "0"
            cam.name = "Web Camera 8"
            cam.status = "online"
            cam.location = "Laptop Webcam"
            print("[Seed] Updated camera 8 as webcam")
        else:
            cam = Camera(
                id=8,
                name="Web Camera 8",
                location="Laptop Webcam",
                channel_no=8,
                stream_url="0",
                status="online"
            )
            db.add(cam)
            print("[Seed] Added camera 8 as webcam")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    add_local_webcam()