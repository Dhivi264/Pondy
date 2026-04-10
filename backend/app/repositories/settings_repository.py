import pyodbc
from app.schemas import SettingsResponse


class SettingsRepository:
    def __init__(self, db: pyodbc.Connection):
        self.db = db

    def get_settings(self) -> SettingsResponse:
        return SettingsResponse(
            theme="dark",
            notifications_enabled=True,
            camera_grid_density="3x3",
            default_archive_filter="all",
            attendance_report_mode="daily",
        )
