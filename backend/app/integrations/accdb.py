import pyodbc
import logging
from typing import List
from app.config import settings

logger = logging.getLogger(__name__)


class ACCDBIntegration:
    """
    Handles synchronization between the Primary DB and the Company MS Access DB.
    Only used for periodic imports/exports as per business requirements.
    """

    def __init__(self):
        self.db_path = settings.ACCDB_PATH

    def _get_connection(self):
        """Standard pyodbc connection string for MS Access."""
        conn_str = (
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
            f"DBQ={self.db_path};"
        )
        return pyodbc.connect(conn_str)

    def import_employees(self) -> List[dict]:
        """Fetch employee master data from MS Access."""
        employees = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT ID, EmployeeID, Name, Department, Role FROM Employees"
                )
                for row in cursor.fetchall():
                    employees.append(
                        {
                            "employee_code": str(row.EmployeeID),
                            "name": row.Name,
                            "department": row.Department,
                            "designation": row.Role,
                        }
                    )
            logger.info(f"[ACCDB] Imported {len(employees)} employees.")
            return employees
        except Exception as e:
            logger.error(f"[ACCDB] Import error: {e}")
            return []

    def export_attendance(self, attendance_data: List[dict]):
        """Write analyzed attendance records back to MS Access."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for record in attendance_data:
                    # Parameterized query to update AttendanceRecords
                    cursor.execute(
                        "INSERT INTO AttendanceRecords (EmployeeID, RecordDate, CheckInTime, CheckOutTime, Status) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            record["employee_code"],
                            record["date"],
                            record["check_in"],
                            record["check_out"],
                            record["status"],
                        ),
                    )
                conn.commit()
            logger.info(f"[ACCDB] Exported {len(attendance_data)} attendance records.")
        except Exception as e:
            logger.error(f"[ACCDB] Export error: {e}")
