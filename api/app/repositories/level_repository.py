"""Acesso aos dados de níveis."""

from sqlalchemy import func, select

from app.models.level import Level
from app.repositories.base_repository import BaseRepository


class LevelRepository(BaseRepository[Level]):
    model = Level

    def list(self) -> list[Level]:
        return list(self.db.scalars(select(Level).order_by(Level.number)))

    def get_by_number(self, number: int) -> Level | None:
        return self.db.scalar(select(Level).where(Level.number == number))

    def max_number(self) -> int:
        return self.db.scalar(select(func.max(Level.number))) or 1
