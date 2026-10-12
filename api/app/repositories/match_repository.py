"""Acesso aos dados de partidas e respostas."""

from sqlalchemy import select

from app.models.match import Match, MatchAnswer
from app.repositories.base_repository import BaseRepository


class MatchRepository(BaseRepository[Match]):
    model = Match

    def get_for_user(self, match_id: int, user_id: int) -> Match | None:
        return self.db.scalar(select(Match).where(Match.id == match_id, Match.user_id == user_id))

    def answered_question_ids(self, match_id: int) -> set[int]:
        return set(
            self.db.scalars(select(MatchAnswer.question_id).where(MatchAnswer.match_id == match_id))
        )

    def add_answer(self, answer: MatchAnswer) -> MatchAnswer:
        self.db.add(answer)
        self.db.flush()
        return answer
