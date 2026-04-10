import threading
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class HealthCheckWorker:
    """
    Background worker that performs health checks every 10 minutes.
    Analyzes camera failures and generates notifications and recommendations.
    """

    def __init__(self, interval_minutes: int = 10):
        self.interval_seconds = interval_minutes * 60  # Convert to seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self):
        """Start the health check worker"""
        if self._running:
            logger.warning("[HealthCheck] Worker is already running.")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("[HealthCheck] Worker started (10-minute interval)")

    def stop(self):
        """Stop the health check worker"""
        logger.info("[HealthCheck] Stopping worker...")
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("[HealthCheck] Worker stopped")

    def _run_loop(self):
        """Main loop for health checks"""
        from app.services.notification_service import NotificationService

        try:
            logger.info("[HealthCheck] Health check loop started")

            while self._running:
                try:
                    logger.info("[HealthCheck] Starting scheduled health scan...")

                    # Perform health check
                    service = NotificationService()
                    scan_log = service.perform_health_check_scan()

                    if scan_log:
                        logger.info(
                            f"[HealthCheck] Scan completed successfully. "
                            f"Scan ID: {scan_log.id}, Online: {scan_log.cameras_online}/{scan_log.total_cameras}"
                        )
                    else:
                        logger.warning("[HealthCheck] Health scan returned None")

                    service.close()

                except Exception as e:
                    logger.error(f"[HealthCheck] Error during scan: {e}", exc_info=True)

                # Wait for next scan interval or until stop is requested
                if self._stop_event.wait(timeout=self.interval_seconds):
                    break

        except Exception as e:
            logger.error(f"[HealthCheck] Critical error in loop: {e}", exc_info=True)
        finally:
            self._running = False
            logger.info("[HealthCheck] Health check loop ended")

    @property
    def is_running(self) -> bool:
        return self._running


# Global instance
health_check_worker = HealthCheckWorker(interval_minutes=10)
