"""Regras de cadastro e login."""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.progress import UserProgress
from app.models.user import User
from app.repositories.progress_repository import ProgressRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(self, db: Session) -> None:
        self.users = UserRepository(db)
        self.progress = ProgressRepository(db)

    def register(self, data: RegisterRequest) -> TokenResponse:
        if self.users.get_by_username(data.username):
            raise ConflictError("Nome de usuário já está em uso")

        user = self.users.add(
            User(username=data.username, password_hash=hash_password(data.password))
        )
        # A jornada nasce junto com a conta.
        self.progress.add(UserProgress(user_id=user.id))
        return TokenResponse(access_token=create_access_token(user.id))

    def login(self, data: LoginRequest) -> TokenResponse:
        user = self.users.get_by_username(data.username)
        if user is None or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("Usuário ou senha inválidos")
        return TokenResponse(access_token=create_access_token(user.id))
