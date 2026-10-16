"""Acesso aos dados de partidas e respostas."""

from datetime import datetime

from sqlalchemy import select, update

from app.models.match import Match, MatchAnswer, MatchStatus
from app.repositories.base_repository import BaseRepository


class MatchRepository(BaseRepository[Match]):
    model = Match

    def get_for_user(self, match_id: int, user_id: int, bloquear: bool = False) -> Match | None:
        """`bloquear` trava a linha até o fim da transação (SELECT ... FOR UPDATE): pedidos
        simultâneos na mesma partida esperam um ao outro em vez de ler o mesmo estado."""
        query = select(Match).where(Match.id == match_id, Match.user_id == user_id)
        if bloquear:
            query = query.with_for_update()
        return self.db.scalar(query)

    def abandon_in_progress(self, user_id: int, ended_at: datetime) -> None:
        """Fecha as partidas que o jogador deixou abertas, sem contar pontos."""
        self.db.execute(
            update(Match)
            .where(Match.user_id == user_id, Match.status == MatchStatus.IN_PROGRESS)
            .values(status=MatchStatus.ABANDONED, ended_at=ended_at, current_question_id=None)
        )

    def answered_question_ids(self, match_id: int) -> set[int]:
        return set(
            self.db.scalars(select(MatchAnswer.question_id).where(MatchAnswer.match_id == match_id))
        )

    def add_answer(self, answer: MatchAnswer) -> MatchAnswer:
        self.db.add(answer)
        self.db.flush()
        return answer
