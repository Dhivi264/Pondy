import pyodbc
from app.schemas import UserProfileResponse


class ProfileRepository:
    def __init__(self, db: pyodbc.Connection):
        self.db = db

    def get_profile(self, user_dict: dict) -> UserProfileResponse:
        return UserProfileResponse(
            id=1, username=user_dict["username"], role=user_dict["role"]
        )
