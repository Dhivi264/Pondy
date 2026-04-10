import cv2
import av
import time
import logging
import sys

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("RTSP-Debugger")

class CameraStreamTester:
    def __init__(self, url: str, name: str = "TestCamera"):
        self.url = url
        self.name = name
        self.retry_count = 0
        self.max_retries = 3
        self.reconnect_delay = 5  # seconds
        self.timeout = 5.0 # seconds

    def test_reachability(self):
        """Phase 1: Basic connection check using PyAV (FFmpeg-based)."""
        logger.info(f"--- Phase 1: Testing Reachability for {self.name} ---")
        logger.info(f"URL: {self.url}")
        
        container = None
        try:
            # Force TCP transport for RTSP (much more stable than UDP over Wi-Fi/Internet)
            options = {
                'rtsp_transport': 'tcp',
                'timeout': str(int(self.timeout * 1000000)), # microseconds
            }
            
            start_time = time.time()
            container = av.open(self.url, options=options, timeout=self.timeout)
            duration = time.time() - start_time
            
            logger.info(f"SUCCESS: Connected to stream in {duration:.2f} seconds.")
            
            # Print Stream Metadata
            for i, stream in enumerate(container.streams):
                logger.info(f"Stream #{i}: {stream.type} (Codec: {stream.name})")
                if stream.type == 'video':
                    logger.info(f"  Resolution: {stream.width}x{stream.height}")
                    logger.info(f"  Pixel Format: {stream.pix_fmt}")
            
            return True
        except av.AVError as e:
            logger.error(f"FAILURE: Could not reach stream. Reason: {e}")
            self._explain_failure(str(e))
            return False
        finally:
            if container:
                container.close()

    def run_live_test_opencv(self):
        """Phase 2: Live frame capture test using OpenCV."""
        logger.info("\n--- Phase 2: Live Frame Capture (OpenCV + FFmpeg Backend) ---")
        
        # Explicitly set the FFmpeg backend for OpenCV to ensure stability
        # and support for authentication in the URL.
        # We also set the transport to TCP via environment variables or backend options if available.
        os_env = {"OPENCV_FFMPEG_CAPTURE_OPTIONS": "rtsp_transport;tcp"}
        import os
        os.environ.update(os_env)

        cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        
        if not cap.isOpened():
            logger.error("OpenCV: Failed to open capture device.")
            return

        logger.info("OpenCV: Capture opened successfully. Reading frames...")
        
        frames_captured = 0
        max_test_frames = 30
        
        try:
            while frames_captured < max_test_frames:
                ret, frame = cap.read()
                if not ret:
                    logger.warning(f"OpenCV: Lost frame at index {frames_captured}. Retrying...")
                    time.sleep(1)
                    continue
                
                frames_captured += 1
                if frames_captured % 10 == 0:
                    logger.info(f"Captured {frames_captured}/{max_test_frames} frames...")
            
            logger.info(f"SUCCESS: Captured {frames_captured} frames successfully.")
        except KeyboardInterrupt:
            logger.info("Test stopped by user.")
        finally:
            cap.release()

    def _explain_failure(self, error_msg: str):
        """Diagnostic explanation based on error codes."""
        msg = error_msg.lower()
        if "invalid data" in msg or "401" in msg or "unauthorized" in msg:
            logger.warning("DIAGNOSIS: CREDENTIALS ISSUE. Check if 'admin' and 'Admin%40123' are correct for this device.")
        elif "connection refused" in msg or "timed out" in msg:
            logger.warning("DIAGNOSIS: NETWORK ISSUE. The IP 192.168.2.30 is likely unreachable or port 554 is blocked.")
        elif "invalid argument" in msg:
            logger.warning("DIAGNOSIS: URL FORMAT ISSUE. Check if the path '/Streaming/Channels/101' matches the camera model.")
        elif "codec" in msg:
            logger.warning("DIAGNOSIS: CODEC ISSUE. The camera might be using H.265 which requires specific system decoders.")
        else:
            logger.warning("DIAGNOSIS: UNKNOWN ISSUE. Likely the stream is private or limited by simultaneous connections.")

if __name__ == "__main__":
    RTSP_URL = "rtsp://admin:Admin%40123@192.168.2.30:554/Streaming/Channels/101"
    
    tester = CameraStreamTester(RTSP_URL, "Hikvision-Cam31")
    
    if tester.test_reachability():
        tester.run_live_test_opencv()
    else:
        logger.info("\nDEBUG TIP: Ensure your computer is on the same 192.168.2.x subnet as the camera.")
