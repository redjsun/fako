"""Acesso aos dados de progresso do jogador."""

from sqlalchemy import select

from app.models.progress import UserProgress
from app.repositories.base_repository import BaseRepository


class ProgressRepository(BaseRepository[UserProgress]):
    model = UserProgress

    def get_by_user(self, user_id: int, bloquear: bool = False) -> UserProgress | None:
        """`bloquear` trava a linha até o fim da transação: dois encerramentos simultâneos
        somam os dois placares em vez de um sobrescrever o outro."""
        query = select(UserProgress).where(UserProgress.user_id == user_id)
        if bloquear:
            query = query.with_for_update()
        return self.db.scalar(query)
