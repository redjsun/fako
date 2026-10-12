"""Jogador do FAKO."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Entity


class User(Entity):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    # A senha nunca é persistida em texto puro.
    password_hash: Mapped[str] = mapped_column(String(255))
    # Responsável pelo conteúdo: pode cadastrar e validar questões.
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
