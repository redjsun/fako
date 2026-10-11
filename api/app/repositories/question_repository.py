"""Acesso aos dados do banco de questões."""

from sqlalchemy import func, or_, select

from app.models.question import Question, QuestionStatus
from app.repositories.base_repository import BaseRepository


class QuestionRepository(BaseRepository[Question]):
    model = Question

    def random_validated(self, exclude_ids: set[int]) -> Question | None:
        """Sorteia uma questão publicada que ainda não saiu na partida."""
        query = select(Question).where(Question.status == QuestionStatus.VALIDATED)
        if exclude_ids:
            query = query.where(Question.id.not_in(exclude_ids))
        return self.db.scalar(query.order_by(func.random()).limit(1))

    def list_by_status(self, status: QuestionStatus | None) -> list[Question]:
        query = select(Question).order_by(Question.id)
        if status is not None:
            query = query.where(Question.status == status)
        return list(self.db.scalars(query))

    def exists_by_statement_or_source(self, statement: str, source: str) -> bool:
        """Já existe questão com o mesmo texto (sem diferenciar caixa) ou a mesma fonte."""
        query = select(Question.id).where(
            or_(func.lower(Question.statement) == statement.lower(), Question.source == source)
        )
        return self.db.scalar(query.limit(1)) is not None
