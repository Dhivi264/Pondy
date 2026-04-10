import pyodbc
from app.schemas import DashboardSummaryResponse


class DashboardRepository:
    def __init__(self, db: pyodbc.Connection):
        self.db = db

    def get_summary(self) -> DashboardSummaryResponse:
        cursor = self.db.cursor()

        def safe_count(table, condition=""):
            try:
                sql = f"SELECT COUNT(ID) FROM {table} {condition}"
                cursor.execute(sql)
                return cursor.fetchone()[0]
            except pyodbc.Error:
                return 0

        total_cams = safe_count("Cameras")
        active_cams = safe_count("Cameras", "WHERE status='online'")
        offline_cams = total_cams - active_cams

        return DashboardSummaryResponse(
            total_cameras=total_cams,
            active_cameras=active_cams,
            offline_cameras=offline_cams,
            employees=safe_count("Employees"),
            attendance_records=safe_count("AttendanceRecords"),
            archive_items=safe_count("ArchiveRecords"),
        )
