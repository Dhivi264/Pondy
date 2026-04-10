from typing import List, Optional
from app.repositories.archive_repository import ArchiveRepository
from app.schemas import ArchiveResponse


class ArchiveService:
    def __init__(self, repo: ArchiveRepository):
        self.repo = repo

    def get_archives(self, record_type: Optional[str]) -> List[ArchiveResponse]:
        return self.repo.get_all(record_type)
