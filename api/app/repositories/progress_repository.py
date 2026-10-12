"""Acesso aos dados de progresso do jogador."""

from sqlalchemy import select

from app.models.progress import UserProgress
from app.repositories.base_repository import BaseRepository


class ProgressRepository(BaseRepository[UserProgress]):
    model = UserProgress

    def get_by_user(self, user_id: int) -> UserProgress | None:
        return self.db.scalar(select(UserProgress).where(UserProgress.user_id == user_id))
