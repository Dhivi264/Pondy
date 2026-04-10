import logging
from sqlalchemy.orm import Session
from app.integrations.accdb import ACCDBIntegration
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.attendance_repository import AttendanceRepository
from app.models.employee import Employee

logger = logging.getLogger(__name__)


class IntegrationService:
    """
    Coordinates synchronization between Primary DB and MS Access.
    """

    def __init__(self, db: Session):
        self.db = db
        self.accdb = ACCDBIntegration()
        self.emp_repo = EmployeeRepository(db)
        self.att_repo = AttendanceRepository(db)

    def sync_employees_from_accdb(self):
        """Import missing employees from MS Access."""
        accdb_employees = self.accdb.import_employees()

        count = 0
        for emp_data in accdb_employees:
            existing = self.emp_repo.get_by_code(emp_data["employee_code"])
            if not existing:
                self.emp_repo.create(Employee(**emp_data))
                count += 1

        return count

    def sync_attendance_to_accdb(self, attendance_date):
        """Export analyzed sessions to MS Access."""
        sessions = self.att_repo.get_sessions_by_date(attendance_date)

        export_data = []
        for sess in sessions:
            # We need to map employee_id back to employee_code
            emp = self.emp_repo.get_by_id(sess.employee_id)
            if emp:
                export_data.append(
                    {
                        "employee_code": emp.employee_code,
                        "date": sess.attendance_date,
                        "check_in": sess.entry_time,
                        "check_out": sess.exit_time,
                        "status": sess.attendance_status,
                    }
                )

        self.accdb.export_attendance(export_data)
        return len(export_data)
