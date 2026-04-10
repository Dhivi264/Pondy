from typing import List
from app.repositories.attendance_repository import AttendanceRepository
from app.schemas import AttendanceResponse, AttendanceSummaryResponse


class AttendanceService:
    def __init__(self, repo: AttendanceRepository):
        self.repo = repo

    def get_all_attendance(self) -> List[AttendanceResponse]:
        return self.repo.get_all()

    def get_stats(self) -> AttendanceSummaryResponse:
        return self.repo.get_stats()
