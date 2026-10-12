"""Modelos de domínio compartilhados pelas demais camadas."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa do SQLAlchemy; seu metadata alimenta as migrations."""


class Entity(Base):
    """Base para as entidades do domínio."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Faz o SQLAlchemy gravar o valor do enum (`"draft"`) e não o nome (`"DRAFT"`)."""
    return [member.value for member in enum_cls]
