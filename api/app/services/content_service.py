"""Curadoria do banco de questões: cadastro e validação humana."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.category import Category
from app.models.question import Question, QuestionOrigin, QuestionStatus
from app.repositories.category_repository import CategoryRepository
from app.repositories.question_repository import QuestionRepository
from app.schemas.admin_schema import (
    QuestionAdminResponse,
    QuestionCreateRequest,
    QuestionReviewRequest,
)
from app.services import game_rules


def to_admin_response(question: Question) -> QuestionAdminResponse:
    return QuestionAdminResponse(
        id=question.id,
        statement=question.statement,
        is_true=question.is_true,
        reliability_reference=question.reliability_reference,
        explanation=question.explanation,
        source=question.source,
        category=question.category.slug,
        status=question.status,
        origin=question.origin,
        validated_at=question.validated_at,
        model_category=question.model_category,
        model_score=question.model_score,
        model_confidence=question.model_confidence,
        model_version=question.model_version,
    )


class ContentService:
    def __init__(self, db: Session) -> None:
        self.questions = QuestionRepository(db)
        self.categories = CategoryRepository(db)

    def get_category(self, slug: str) -> Category:
        category = self.categories.get_by_slug(slug)
        if category is None:
            raise NotFoundError(f"Categoria '{slug}' não encontrada")
        return category

    def list(self, status: QuestionStatus | None) -> list[QuestionAdminResponse]:
        return [to_admin_response(q) for q in self.questions.list_by_status(status)]

    def create(self, data: QuestionCreateRequest) -> QuestionAdminResponse:
        # Mesmo conteúdo humano entra como rascunho até ser revisado.
        question = self.questions.add(
            Question(
                statement=data.statement,
                is_true=data.is_true,
                reliability_reference=(
                    data.reliability_reference
                    if data.reliability_reference is not None
                    else game_rules.default_reliability_reference(data.is_true)
                ),
                explanation=data.explanation,
                source=data.source,
                category=self.get_category(data.category),
                status=QuestionStatus.DRAFT,
                origin=QuestionOrigin.HUMAN,
            )
        )
        return to_admin_response(question)

    def review(self, question_id: int, data: QuestionReviewRequest) -> QuestionAdminResponse:
        question = self.questions.get(question_id)
        if question is None:
            raise NotFoundError("Questão não encontrada")
        if question.status != QuestionStatus.DRAFT:
            raise BusinessRuleError("Só rascunhos podem ser revisados")

        question.status = QuestionStatus.VALIDATED if data.approve else QuestionStatus.REJECTED
        # Só a aprovação conta como validação; a rejeitada fica sem data de publicação.
        question.validated_at = datetime.now(timezone.utc) if data.approve else None
        return to_admin_response(question)
