from app.db import SessionLocal
from app.models.camera import Camera
import urllib.parse

def bulk_add_cameras():
    db = SessionLocal()
    try:
        # Range of IPs: 192.168.2.21 to 192.168.2.52
        start_suffix = 21
        end_suffix = 52
        
        # Credentials and path
        username = "admin"
        password = "Admin@123"
        # URL encode password for safety in RTSP URL
        encoded_password = urllib.parse.quote(password)
        
        print(f"Starting bulk update of cameras from .21 to .52...")
        
        added_count = 0
        updated_count = 0
        
        for i in range(start_suffix, end_suffix + 1):
            ip = f"192.168.2.{i}"
            stream_url = f"rtsp://{username}:{encoded_password}@{ip}:554/Streaming/Channels/101"
            name = f"Camera {i}"
            
            # Check if camera with this IP already exists
            # We search for the IP in the stream_url to identify it
            existing_cam = db.query(Camera).filter(Camera.stream_url.contains(ip)).first()
            
            if existing_cam:
                print(f"UPDATING: Found existing camera (ID: {existing_cam.id}) for IP {ip}")
                existing_cam.name = name
                existing_cam.stream_url = stream_url
                existing_cam.status = "online"
                updated_count += 1
            else:
                print(f"ADDING: Creating new entry for Camera {i} (IP: {ip})")
                new_cam = Camera(
                    name=name,
                    stream_url=stream_url,
                    status="online",
                    channel_no=i
                )
                db.add(new_cam)
                added_count += 1
        
        db.commit()
        print(f"\nSummary:")
        print(f"Total processed: {end_suffix - start_suffix + 1}")
        print(f"New cameras added: {added_count}")
        print(f"Existing cameras updated: {updated_count}")
        print("Database update successful.")
        
    except Exception as e:
        db.rollback()
        print(f"Error updating database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    bulk_add_cameras()
