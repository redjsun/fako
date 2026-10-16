"""Hash de senhas e tokens de acesso."""

from datetime import datetime, timedelta, timezone
from functools import lru_cache

import bcrypt
import jwt

from app.core.config import get_settings

# Fixo no código: o algoritmo não vem de configuração, para nunca aceitar "none" ou outro.
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


@lru_cache
def _hash_ficticio() -> str:
    return hash_password("senha-ficticia-so-para-gastar-o-mesmo-tempo")


def gastar_tempo_de_verificacao(password: str) -> None:
    """Login de usuário que não existe: roda o bcrypt mesmo assim, para o tempo da resposta não
    revelar quais nomes estão cadastrados."""
    verify_password(password, _hash_ficticio())


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {"sub": str(user_id), "exp": expires_at, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.exigir_segredo_jwt(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Retorna o id do usuário do token, ou None se o token for inválido/expirado."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.exigir_segredo_jwt(), algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
