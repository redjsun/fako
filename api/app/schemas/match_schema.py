"""DTOs de partida, respostas e resultado."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.match import MatchStatus
from app.schemas.level_schema import LevelResponse


class MatchStartRequest(BaseModel):
    # Se omitido, a partida começa no nível atual do jogador.
    level: int | None = None


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: LevelResponse
    score: int
    status: MatchStatus
    duration_seconds: int
    started_at: datetime
    ended_at: datetime | None


class AnswerRequest(BaseModel):
    question_id: int
    answer: bool


class ModelGuess(BaseModel):
    """Palpite do classificador sobre a afirmação, mostrado depois da resposta do jogador."""

    category: str  # falso, enganoso, confere ou incerto (confiança abaixo do limiar)
    score: float | None  # 0 a 100; sem nota quando incerto
    confidence: float
    model_version: str


class AnswerResultResponse(BaseModel):
    is_correct: bool
    correct_answer: bool
    explanation: str
    source: str
    score: int
    model_guess: ModelGuess | None = None


class MatchResultResponse(BaseModel):
    match: MatchResponse
    advanced: bool
    current_level: int
