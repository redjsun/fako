"""Regras de cadastro e login."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.rate_limit import limite_de_login
from app.core.security import (
    create_access_token,
    gastar_tempo_de_verificacao,
    hash_password,
    verify_password,
)
from app.models.progress import UserProgress
from app.models.user import User
from app.repositories.progress_repository import ProgressRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import LoginRequest, RegisterRequest, TokenResponse

NOME_EM_USO = "Nome de usuário já está em uso"


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.progress = ProgressRepository(db)

    def register(self, data: RegisterRequest) -> TokenResponse:
        if self.users.get_by_username(data.username):
            raise ConflictError(NOME_EM_USO)

        # Dois cadastros simultâneos com o mesmo nome passam pela checagem acima; o índice único
        # barra o segundo, que vira 409 em vez de erro 500.
        try:
            with self.db.begin_nested():
                user = self.users.add(
                    User(username=data.username, password_hash=hash_password(data.password))
                )
        except IntegrityError as erro:
            raise ConflictError(NOME_EM_USO) from erro
        # A jornada nasce junto com a conta.
        self.progress.add(UserProgress(user_id=user.id))
        return TokenResponse(access_token=create_access_token(user.id))

    def login(self, data: LoginRequest, origem: str) -> TokenResponse:
        limite_de_login.verificar(origem, data.username)
        user = self.users.get_by_username(data.username)
        if user is None:
            gastar_tempo_de_verificacao(data.password)
        if user is None or not verify_password(data.password, user.password_hash):
            limite_de_login.registrar_falha(origem, data.username)
            raise UnauthorizedError("Usuário ou senha inválidos")
        limite_de_login.registrar_sucesso(origem, data.username)
        return TokenResponse(access_token=create_access_token(user.id))
