from app.db import SessionLocal
from app.models.camera import Camera

def update_cameras():
    db = SessionLocal()
    try:
        # Update Camera 8
        cam8 = db.query(Camera).filter(Camera.id == 8).first()
        if cam8:
            print(f"Updating Camera 8 (ID: 8)...")
            cam8.name = "Camera 8"
            cam8.stream_url = "rtsp://admin:Admin%40123@192.168.2.20:554/Streaming/Channels/101"
            cam8.status = "online"
        else:
            print(f"Camera 8 not found, creating...")
            cam8 = Camera(
                id=8,
                name="Camera 8",
                stream_url="rtsp://admin:Admin%40123@192.168.2.20:554/Streaming/Channels/101",
                status="online"
            )
            db.add(cam8)

        # Update Camera 32 (ID 7)
        cam32 = db.query(Camera).filter(Camera.id == 7).first()
        if cam32:
            print(f"Updating Camera 32 (ID: 7)...")
            cam32.name = "Camera 32"
            cam32.stream_url = "rtsp://admin:Admin%40123@192.168.2.37:554/Streaming/Channels/101"
            cam32.status = "online"
        else:
            print(f"Camera ID 7 not found, searching for name 'cam_32'...")
            cam32_by_name = db.query(Camera).filter(Camera.name == "cam_32").first()
            if cam32_by_name:
                print(f"Updating camera with name 'cam_32' (ID: {cam32_by_name.id})...")
                cam32_by_name.name = "Camera 32"
                cam32_by_name.stream_url = "rtsp://admin:Admin%40123@192.168.2.37:554/Streaming/Channels/101"
            else:
                print(f"No existing Camera 32 found. Creating with ID 32...")
                new_cam32 = Camera(
                    id=32,
                    name="Camera 32",
                    stream_url="rtsp://admin:Admin%40123@192.168.2.37:554/Streaming/Channels/101",
                    status="online"
                )
                db.add(new_cam32)

        db.commit()
        print("Successfully updated database.")
    except Exception as e:
        db.rollback()
        print(f"Error updating database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_cameras()
