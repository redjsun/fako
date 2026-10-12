"""Nível de dificuldade da partida."""

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Entity


class Level(Entity):
    __tablename__ = "levels"

    number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    # Níveis 1–3 usam 7×7 e níveis 4–6 usam 6×6.
    board_size: Mapped[int] = mapped_column(Integer)
    # Intervalo entre movimentos da cobra; menor = mais difícil.
    tick_ms: Mapped[int] = mapped_column(Integer)
    # Pontuação mínima na partida para liberar o próximo nível.
    min_score_to_advance: Mapped[int] = mapped_column(Integer)
