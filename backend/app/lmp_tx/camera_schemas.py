"""
Extended Camera Schemas — RTSP + Hardware-Aware
Adds to the existing CameraCreate / CameraResponse in schemas.py
"""

from pydantic import BaseModel, Field, field_validator
from enum import Enum


class StreamQuality(str, Enum):
    MAIN = "main"
    SUB = "sub"
    MOBILE = "mobile"


class HardwareProfileEnum(str, Enum):
    SERVER_GPU = "server_gpu"
    WORKSTATION = "workstation"
    JETSON_NANO = "jetson_nano"
    INTEL_NCS = "intel_ncs"
    RASPBERRY_PI = "raspberry_pi"
    AUTO = "auto"


class RTSPCameraCreate(BaseModel):
    """Request body for registering a camera with a full RTSP config."""

    camera_id: str
    name: str
    manufacturer: str = "generic"
    ip_address: str
    rtsp_user: str = "admin"
    rtsp_password: str
    channel: int = Field(1, ge=1, le=64)
    quality: StreamQuality = StreamQuality.MAIN

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        import re

        pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        if not re.match(pattern, v):
            raise ValueError(f"Invalid IP address: {v}")
        return v


class RTSPCameraResponse(BaseModel):
    camera_id: str
    name: str
    manufacturer: str
    masked_url: str  # password replaced with ***
    channel: int
    quality: StreamQuality
    is_alive: bool
    probe_message: str


class FrameSkipStatusResponse(BaseModel):
    camera_id: str
    current_skip_rate: int
    total_frames_received: int
    total_frames_processed: int
    avg_inference_ms: float
    effective_fps: float


class HardwareProfileResponse(BaseModel):
    detected_profile: str
    yolo_variant: str
    yolo_backend: str
    default_skip_rate: int
    max_resolution_w: int
    max_resolution_h: int
    notes: str
