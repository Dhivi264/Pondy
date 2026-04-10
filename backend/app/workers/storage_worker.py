import os
import time
import shutil
import logging
import threading
from glob import glob
from app.config import settings

logger = logging.getLogger(__name__)

class StorageWorker:
    """
    Background worker that monitors disk usage where video recordings are stored.
    Automatically deletes the oldest footage to prevent system crashes from full disks.
    """
    def __init__(self, interval_seconds=3600, max_usage_percent=85.0):
        self.interval_seconds = interval_seconds
        self.max_usage_percent = max_usage_percent
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        logger.info(f"[StorageWorker] Started. Polling every {self.interval_seconds}s. Max Usage: {self.max_usage_percent}%")
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            logger.info("[StorageWorker] Stopped.")

    def _run_loop(self):
        while self._running:
            self._check_and_clean()
            # Sleep in small chunks to allow quick termination on shutdown
            for _ in range(self.interval_seconds):
                if not self._running:
                    break
                time.sleep(1)

    def _check_and_clean(self):
        try:
            recordings_path = os.path.abspath(settings.RECORDINGS_DIR)
            if not os.path.exists(recordings_path):
                return
                
            total, used, free = shutil.disk_usage(recordings_path)
            usage_percent = (used / total) * 100.0
            
            if usage_percent > self.max_usage_percent:
                logger.warning(f"[StorageWorker] Disk usage {usage_percent:.1f}% exceeds limit {self.max_usage_percent}%. Cleaning up...")
                # Aim to clean up to 5% below maximum to give buffer
                self._delete_oldest_files_until_healthy(recordings_path, target_percent=self.max_usage_percent - 5.0)
                
        except Exception as e:
            logger.error(f"[StorageWorker] Error checking storage: {e}")

    def _delete_oldest_files_until_healthy(self, directory_path: str, target_percent: float):
        try:
            # Get all mp4 files, sorted by oldest first
            files = glob(os.path.join(directory_path, "*.mp4"))
            files.sort(key=os.path.getmtime)
            
            deleted_count = 0
            for file_path in files:
                total, used, free = shutil.disk_usage(directory_path)
                usage_percent = (used / total) * 100.0
                if usage_percent <= target_percent:
                    logger.info(f"[StorageWorker] Healthy usage reached ({usage_percent:.1f}%). Deleted {deleted_count} files.")
                    break
                    
                os.remove(file_path)
                deleted_count += 1
                logger.info(f"[StorageWorker] Deleted old footage: {file_path}")
        except Exception as e:
            logger.error(f"[StorageWorker] Error during cleanup logic: {e}")

storage_worker = StorageWorker()
