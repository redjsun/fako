"""Apoio da IA ao conteúdo: tudo que ela gera entra como rascunho."""

from sqlalchemy.orm import Session

from app.integrations.ai_client import AIClient
from app.models.question import Question, QuestionOrigin, QuestionStatus
from app.repositories.question_repository import QuestionRepository
from app.schemas.admin_schema import (
    AIClassifyRequest,
    AIClassifyResponse,
    AIGenerateRequest,
    QuestionAdminResponse,
)
from app.services import game_rules
from app.services.content_service import ContentService, to_admin_response


class AIService:
    def __init__(self, db: Session, ai_client: AIClient) -> None:
        self.ai = ai_client
        self.questions = QuestionRepository(db)
        self.content = ContentService(db)

    def generate(self, data: AIGenerateRequest) -> list[QuestionAdminResponse]:
        category = self.content.get_category(data.category)
        generated = self.ai.generate_questions(category.name, data.quantity)
        # Nunca publica direto; a revisão acontece em /admin/questions/{id}/review.
        drafts = [
            self.questions.add(
                Question(
                    statement=item.statement,
                    is_true=item.is_true,
                    reliability_reference=game_rules.default_reliability_reference(item.is_true),
                    explanation=item.explanation,
                    source=item.source,
                    category=category,
                    status=QuestionStatus.DRAFT,
                    origin=QuestionOrigin.AI,
                )
            )
            for item in generated
        ]
        return [to_admin_response(q) for q in drafts]

    def classify(self, data: AIClassifyRequest) -> AIClassifyResponse:
        result = self.ai.classify(data.statement)
        return AIClassifyResponse(
            suggested_is_true=result.suggested_is_true,
            confidence=result.confidence,
            rationale=result.rationale,
        )
