from app.repositories.profile_repository import ProfileRepository
from app.schemas import UserProfileResponse


class ProfileService:
    def __init__(self, repo: ProfileRepository):
        self.repo = repo

    def get_profile(self, user_dict: dict) -> UserProfileResponse:
        return self.repo.get_profile(user_dict)
