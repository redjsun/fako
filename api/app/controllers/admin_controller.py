"""Rotas de curadoria de conteúdo e ferramentas de IA (restritas a administradores)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.integrations.classificador_client import ClassificadorClient, get_classificador
from app.integrations.llm_client import LLMClient, get_llm_client
from app.integrations.noticias_client import NoticiasClient, get_noticias_clients
from app.models.question import QuestionStatus
from app.schemas.admin_schema import (
    AIClassifyRequest,
    AIClassifyResponse,
    AIGenerateRequest,
    ClassifierAnalyzeRequest,
    ClassifierAnalyzeResponse,
    NewsImportRequest,
    NewsImportResponse,
    QuestionAdminResponse,
    QuestionCreateRequest,
    QuestionReviewRequest,
)
from app.services.ai_service import AIService
from app.services.classificador_service import ClassificadorService
from app.services.content_service import ContentService
from app.services.noticias_service import NoticiasService

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


def get_content_service(db: Session = Depends(get_db)) -> ContentService:
    return ContentService(db)


def get_ai_service(
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
    classificador: ClassificadorClient = Depends(get_classificador),
    noticias: list[NoticiasClient] = Depends(get_noticias_clients),
) -> AIService:
    return AIService(db, llm, classificador, noticias)


def get_classify_service(
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
    classificador: ClassificadorClient = Depends(get_classificador),
) -> AIService:
    # Sem notícias: um NOTICIAS_PROVIDER mal configurado não derruba a análise.
    return AIService(db, llm, classificador)


@router.get("/questions", response_model=list[QuestionAdminResponse])
def list_questions(
    status: QuestionStatus | None = None,
    service: ContentService = Depends(get_content_service),
) -> list[QuestionAdminResponse]:
    return service.list(status)


@router.post(
    "/questions", response_model=QuestionAdminResponse, status_code=status.HTTP_201_CREATED
)
def create_question(
    data: QuestionCreateRequest, service: ContentService = Depends(get_content_service)
) -> QuestionAdminResponse:
    return service.create(data)


@router.patch("/questions/{question_id}/review", response_model=QuestionAdminResponse)
def review_question(
    question_id: int,
    data: QuestionReviewRequest,
    service: ContentService = Depends(get_content_service),
) -> QuestionAdminResponse:
    return service.review(question_id, data)


@router.post(
    "/ai/generate",
    response_model=list[QuestionAdminResponse],
    status_code=status.HTTP_201_CREATED,
)
def generate_questions(
    data: AIGenerateRequest, service: AIService = Depends(get_ai_service)
) -> list[QuestionAdminResponse]:
    """Checagens de agência reescritas pela LLM viram rascunhos, com o gabarito da checagem."""
    return service.generate(data)


@router.post("/ai/classify", response_model=AIClassifyResponse)
def classify_statement(
    data: AIClassifyRequest, service: AIService = Depends(get_classify_service)
) -> AIClassifyResponse:
    return service.classify(data)


def get_noticias_service(
    db: Session = Depends(get_db),
    noticias: list[NoticiasClient] = Depends(get_noticias_clients),
    classificador: ClassificadorClient = Depends(get_classificador),
) -> NoticiasService:
    return NoticiasService(db, noticias, classificador)


@router.post("/news/import", response_model=NewsImportResponse, status_code=status.HTTP_201_CREATED)
def import_news(
    data: NewsImportRequest, service: NoticiasService = Depends(get_noticias_service)
) -> NewsImportResponse:
    """Busca manchetes no provedor de notícias e grava as que servem como rascunhos."""
    return service.importar(data)


@router.post("/classifier/analyze", response_model=ClassifierAnalyzeResponse)
def analyze_with_classifier(
    data: ClassifierAnalyzeRequest,
    classificador: ClassificadorClient = Depends(get_classificador),
) -> ClassifierAnalyzeResponse:
    """Análise do classificador publicado em models/atual, com os termos que mais pesaram."""
    return ClassificadorService(classificador).analisar(data.statement)
