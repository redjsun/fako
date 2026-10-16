"""DTOs de partida, respostas e resultado."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.match import MatchStatus
from app.schemas.level_schema import LevelResponse


class MatchStartRequest(BaseModel):
    # Se omitido, a partida começa no nível atual do jogador.
    level: int | None = Field(default=None, ge=1)


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
    # Barra de confiabilidade do jogo: 0 = nada confiável, 100 = totalmente confiável.
    reliability: int = Field(ge=0, le=100)


class ModelGuess(BaseModel):
    """Palpite do classificador sobre a afirmação, mostrado depois da resposta do jogador."""

    category: str  # falso, enganoso, confere ou incerto (confiança abaixo do limiar)
    score: float | None  # 0 a 100; sem nota quando incerto
    confidence: float
    model_version: str


class ClaimOriginResponse(BaseModel):
    """Onde a afirmação circulou (checagem) ou foi publicada (manchete), depois da resposta."""

    kind: str  # "alegacao" (circulou; a checagem fica em `source`) ou "materia" (veículo)
    author: str  # "redes sociais", "WhatsApp", o nome de quem disse ou o veículo
    when: date | None
    link: str | None  # a matéria, nas manchetes; nas alegações a API não traz o post


class AnswerResultResponse(BaseModel):
    is_correct: bool
    correct_answer: bool
    reliability: int
    reliability_reference: int
    tolerance: int
    distance: int
    explanation: str
    source: str
    score: int
    # Resposta depois do tempo da pergunta (com a folga do servidor): conta como erro.
    timed_out: bool = False
    model_guess: ModelGuess | None = None
    claim_origin: ClaimOriginResponse | None = None


class MatchResultResponse(BaseModel):
    match: MatchResponse
    advanced: bool
    current_level: int
