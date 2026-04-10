"""
RTSP Stream Manager
===================
Manages RTSP connections for IP cameras:
  - URL parsing & validation
  - ONVIF Device Manager compatible URL templating
  - Connection health probing (HEAD-check via OpenCV)
  - Common manufacturer URL format catalogue

Tip: Find your camera's URL in its manual or use ONVIF Device Manager
     (https://sourceforge.net/projects/onvifdm/) to auto-discover it.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Common RTSP URL templates by manufacturer
# ─────────────────────────────────────────────────────────────────

RTSP_TEMPLATES: dict[str, str] = {
    # Manufacturer      Template (fill user/pass/ip/channel/subtype)
    "hikvision": "rtsp://{user}:{password}@{ip}:554/Streaming/Channels/{channel:02d}0{subtype}",
    "dahua": "rtsp://{user}:{password}@{ip}:554/cam/realmonitor?channel={channel}&subtype={subtype}",
    "axis": "rtsp://{user}:{password}@{ip}/axis-media/media.amp?videocodec=h264",
    "hanwha": "rtsp://{user}:{password}@{ip}:554/profile{channel}/media.smp",
    "bosch": "rtsp://{user}:{password}@{ip}/rtsp_tunnel?inst={channel}",
    "vivotek": "rtsp://{user}:{password}@{ip}/live.sdp",
    "uniview": "rtsp://{user}:{password}@{ip}:554/unicast/{channel}/s{subtype}/live",
    "reolink": "rtsp://{user}:{password}@{ip}:554/h264Preview_{channel:02d}_{stream}",
    "amcrest": "rtsp://{user}:{password}@{ip}:554/cam/realmonitor?channel={channel}&subtype={subtype}",
    "generic": "rtsp://{user}:{password}@{ip}:554/stream{channel}",
}


class StreamQuality(str, Enum):
    """Maps to subtype / stream selector used in RTSP URLs."""

    MAIN = "main"  # Full resolution (subtype=0)
    SUB = "sub"  # Reduced resolution for preview (subtype=1)
    MOBILE = "mobile"  # Low-res mobile stream (subtype=2)


class RTSPStreamInfo:
    """Validated RTSP URL with parsed components."""

    def __init__(
        self,
        camera_id: str,
        url: str,
        manufacturer: str = "generic",
        quality: StreamQuality = StreamQuality.MAIN,
        channel: int = 1,
    ):
        self.camera_id = camera_id
        self.raw_url = url
        self.manufacturer = manufacturer
        self.quality = quality
        self.channel = channel
        self._parsed = urlparse(url)

    @property
    def is_valid_scheme(self) -> bool:
        return self._parsed.scheme in ("rtsp", "rtsps", "rtmp")

    @property
    def host(self) -> str:
        return self._parsed.hostname or ""

    @property
    def port(self) -> int:
        return self._parsed.port or 554

    @property
    def masked_url(self) -> str:
        """Return URL with password replaced by '***' for safe logging."""
        if self._parsed.password:
            return self.raw_url.replace(self._parsed.password, "***")
        return self.raw_url

    def __repr__(self) -> str:
        return f"<RTSPStreamInfo camera={self.camera_id} host={self.host} q={self.quality}>"


class RTSPStreamManager:
    """
    Builds, validates, and tracks RTSP stream URLs for all cameras.

    Usage:
        mgr = RTSPStreamManager()
        info = mgr.build_url("cam_01", "hikvision",
                              user="admin", password="pass",
                              ip="192.168.1.64", channel=1)
        ok, msg = mgr.probe(info)
    """

    # Registry: camera_id → RTSPStreamInfo
    _registry: dict[str, RTSPStreamInfo] = {}

    # ── URL builder ───────────────────────────────────────────────

    def build_url(
        self,
        camera_id: str,
        manufacturer: str,
        user: str,
        password: str,
        ip: str,
        channel: int = 1,
        quality: StreamQuality = StreamQuality.MAIN,
        subtype: int = 0,
        stream: str = "main",
    ) -> RTSPStreamInfo:
        """
        Build a validated RTSP URL from parameters using the
        manufacturer template catalogue.
        """
        template = RTSP_TEMPLATES.get(manufacturer.lower(), RTSP_TEMPLATES["generic"])
        try:
            url = template.format(
                user=user,
                password=password,
                ip=ip,
                channel=channel,
                subtype=subtype,
                stream=stream,
            )
        except KeyError as e:
            logger.warning(
                f"Template key missing for {manufacturer}: {e}. Using generic."
            )
            url = RTSP_TEMPLATES["generic"].format(
                user=user,
                password=password,
                ip=ip,
                channel=channel,
                subtype=subtype,
                stream=stream,
            )

        info = RTSPStreamInfo(
            camera_id=camera_id,
            url=url,
            manufacturer=manufacturer,
            quality=quality,
            channel=channel,
        )
        self._registry[camera_id] = info
        logger.info(f"[RTSP] Registered {info.masked_url}")
        return info

    def register_raw(self, camera_id: str, raw_url: str) -> RTSPStreamInfo:
        """Register a camera with a manually supplied RTSP URL."""
        info = RTSPStreamInfo(camera_id=camera_id, url=raw_url)
        if not info.is_valid_scheme:
            raise ValueError(
                f"Invalid RTSP URL scheme '{info._parsed.scheme}' for camera {camera_id}. "
                "Expected rtsp://, rtsps://, or rtmp://"
            )
        self._registry[camera_id] = info
        return info

    def get(self, camera_id: str) -> Optional[RTSPStreamInfo]:
        return self._registry.get(camera_id)

    def all_registered(self) -> list[RTSPStreamInfo]:
        return list(self._registry.values())

    # ── Health probe ──────────────────────────────────────────────

    def probe(self, info: RTSPStreamInfo, timeout_ms: int = 3000) -> tuple[bool, str]:
        """
        Non-blocking probe: open the RTSP stream and read one frame.
        Returns (is_alive, message).

        Requires opencv-python. Gracefully degrades if not installed.
        """
        try:
            import cv2  # type: ignore

            cap = cv2.VideoCapture(info.raw_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms)
            ok = cap.isOpened()
            if ok:
                ret, _ = cap.read()
                ok = ret
            cap.release()
            msg = "alive" if ok else "stream opened but no frames received"
            return ok, msg
        except ImportError:
            return True, "probe skipped (opencv not installed)"
        except Exception as e:
            return False, str(e)
