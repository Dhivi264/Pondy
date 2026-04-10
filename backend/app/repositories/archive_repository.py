import os
import uuid
from datetime import datetime
from typing import List, Optional
from app.schemas import ArchiveResponse

class ArchiveRepository:
    def __init__(self, db=None):
        self.db = db
        # Base directory where clips are stored
        self.base_dir = "data"
        self.recordings_dir = os.path.join(self.base_dir, "recordings")
        self.faces_dir = os.path.join(self.base_dir, "captured_faces")

    def get_all(self, record_type: Optional[str] = None) -> List[ArchiveResponse]:
        archives = []

        # Helper to process a directory
        def scan_dir(directory: str, default_type: str):
            if not os.path.exists(directory):
                return
            for entry in os.scandir(directory):
                if entry.is_file():
                    filename = entry.name
                    # Try to parse camera_id and timestamp from filename: camera_8_YYYYMMDD_HHMMSS.ext
                    parts = filename.split('_')
                    camera_id = "unknown"
                    start_time = datetime.fromtimestamp(entry.stat().st_ctime)

                    if len(parts) >= 3:
                        camera_id = parts[0] + "_" + parts[1]
                        try:
                            # If format is camera_8_20260408_110609.avi
                            date_str = parts[-2]
                            time_str = parts[-1].split('.')[0]
                            start_time = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                            camera_id = "_".join(parts[:-2])
                        except ValueError:
                            pass

                    archives.append(
                        ArchiveResponse(
                            id=str(uuid.uuid4()),
                            archive_id=filename,
                            camera_id=camera_id,
                            record_type=default_type,
                            duration=60, # Mock duration
                            file_size=entry.stat().st_size,
                            file_path=os.path.join(directory, filename),
                            start_time=start_time
                        )
                    )

        # Scan directories
        if record_type in [None, "video"]:
            scan_dir(self.recordings_dir, "video")
        if record_type in [None, "face"]:
            scan_dir(self.faces_dir, "face")

        # Sort by start_time descending
        archives.sort(key=lambda x: x.start_time, reverse=True)
        return archives
