from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, date

# ── Auth Schemas ──────────────────────────────────────────────


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


# ── Employee Schemas ──────────────────────────────────────────


class EmployeeBase(BaseModel):
    employee_code: Optional[str] = None
    employee_id: Optional[str] = None
    name: str
    department: Optional[str] = None
    designation: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class EmployeeCreate(EmployeeBase):
    role: Optional[str] = None
    face_image_base64: Optional[str] = None
    images: Optional[List[str]] = []
    has_face_enrolled: Optional[bool] = False  # Acceptance from Flutter


class EmployeeResponse(EmployeeBase):
    id: int
    is_active: bool
    has_face_enrolled: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# ── Camera Schemas ────────────────────────────────────────────


class CameraBase(BaseModel):
    name: str
    stream_url: str
    location: Optional[str] = None
    is_entry_camera: bool = False
    is_exit_camera: bool = False


class CameraResponse(CameraBase):
    id: int
    status: str
    public_url: Optional[str] = None
    stream_url: Optional[str] = None   # overwritten by router with MJPEG endpoint
    fps: int = 15                       # maps to frame_rate on ORM
    channel: int = 1                    # maps to channel_no on ORM
    is_ai_active: bool = False
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

        @staticmethod
        def alias_generator(string: str) -> str:
            temp = string.split("_")
            return temp[0] + "".join(ele.title() for ele in temp[1:])


# ── Attendance Schemas ────────────────────────────────────────


class AttendanceSessionResponse(BaseModel):
    id: int
    employee_id: int
    attendance_date: date
    entry_time: Optional[datetime]
    exit_time: Optional[datetime]
    attendance_status: str
    cameras_spotted_count: int
    total_visible_duration_seconds: int

    class Config:
        from_attributes = True
        populate_by_name = True

        @staticmethod
        def alias_generator(string: str) -> str:
            temp = string.split("_")
            return temp[0] + "".join(ele.title() for ele in temp[1:])


class AttendanceSummaryStats(BaseModel):
    total_employees: int
    present_today: int
    absent_today: int
    total_cameras: int
    active_cameras: int
    avg_ai_latency_ms: float = 0.0
    global_ai_fps: float = 0.0

    class Config:
        populate_by_name = True

        @staticmethod
        def alias_generator(string: str) -> str:
            temp = string.split("_")
            return temp[0] + "".join(ele.title() for ele in temp[1:])


# ── Dashboard Schemas ─────────────────────────────────────────


class DashboardSummary(BaseModel):
    total_cameras: int
    active_cameras: int
    offline_cameras: int
    employees: int
    present_today: int
    absent_today: int
    archive_items: int
    anomalies: int = 0
    al_samples: int = 0
    avg_ai_latency_ms: float = 0.0
    global_ai_fps: float = 0.0

    class Config:
        populate_by_name = True

        @staticmethod
        def alias_generator(string: str) -> str:
            temp = string.split("_")
            return temp[0] + "".join(ele.title() for ele in temp[1:])


# ── Integration Schemas ───────────────────────────────────────


class SyncResponse(BaseModel):
    items_synced: int
    message: str


class ArchiveResponse(BaseModel):
    id: str
    archive_id: str
    camera_id: str
    record_type: str
    duration: int
    file_size: int
    file_path: str
    start_time: datetime

