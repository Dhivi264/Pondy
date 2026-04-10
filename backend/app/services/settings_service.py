from app.repositories.settings_repository import SettingsRepository
from app.schemas import SettingsResponse


class SettingsService:
    def __init__(self, repo: SettingsRepository):
        self.repo = repo

    def get_settings(self) -> SettingsResponse:
        return self.repo.get_settings()
