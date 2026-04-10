from app.repositories.auth_repository import AuthRepository
from app.auth import verify_password, create_access_token
from app.schemas import TokenResponse
from fastapi import HTTPException, status


class AuthService:
    def __init__(self, auth_repo: AuthRepository):
        self.auth_repo = auth_repo

    def authenticate_admin(self, username: str, password: str) -> TokenResponse:
        admin = self.auth_repo.get_admin_by_username(username)
        if not admin or not verify_password(password, admin["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

        access_token = create_access_token(
            data={"sub": admin["username"], "role": admin["role"]}
        )
        return TokenResponse(access_token=access_token)
