"""Categoria das questões: Saúde, Tecnologia, Conhecimentos Gerais."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Entity


class Category(Entity):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
