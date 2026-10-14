"""DTOs da curadoria de conteúdo e das ferramentas de IA."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.question import QuestionOrigin, QuestionStatus


class QuestionCreateRequest(BaseModel):
    statement: str = Field(min_length=5)
    is_true: bool
    # Se omitida, deriva de is_true (90 ou 10).
    reliability_reference: int | None = Field(default=None, ge=0, le=100)
    explanation: str = Field(min_length=5)
    source: str = Field(min_length=2, max_length=500)
    category: str  # Slug da categoria


class QuestionReviewRequest(BaseModel):
    approve: bool


class QuestionAdminResponse(BaseModel):
    id: int
    statement: str
    is_true: bool
    reliability_reference: int
    explanation: str
    source: str
    category: str
    status: QuestionStatus
    origin: QuestionOrigin
    validated_at: datetime | None
    # Análise do classificador na curadoria; vazia nas questões cadastradas sem ele.
    model_category: str | None = None
    model_score: float | None = None
    model_confidence: float | None = None
    model_version: str | None = None
    # Afirmação classificada (modelo padronizado) e onde a alegação circulou.
    claim_text: str | None = None
    origin_author: str | None = None
    origin_link: str | None = None
    origin_date: date | None = None


class AIGenerateRequest(BaseModel):
    category: str  # Slug da categoria
    quantity: int = Field(default=3, ge=1, le=10)


class AIClassifyRequest(BaseModel):
    statement: str = Field(min_length=5)


class AIClassifyResponse(BaseModel):
    suggested_is_true: bool
    confidence: float
    rationale: str


class NewsImportRequest(BaseModel):
    # As notícias vêm de todos os assuntos; a categoria só existe porque a questão exige uma.
    category: str = "conhecimentos-gerais"  # Slug da categoria
    quantity: int = Field(default=5, ge=1, le=10)


class NewsDiscarded(BaseModel):
    title: str
    reason: str


class NewsImportResponse(BaseModel):
    imported: list[QuestionAdminResponse]
    discarded: list[NewsDiscarded]


class ClassifierAnalyzeRequest(BaseModel):
    statement: str = Field(min_length=5, max_length=1000)


class ClassifierAnalyzeResponse(BaseModel):
    statement: str
    normalized_statement: str
    category: str
    score: float | None
    confidence: float
    probabilities: dict[str, float]
    model_version: str
    # Termos que mais pesaram (negativo puxa para falso); só o admin vê.
    contributions: list[tuple[str, float]]
