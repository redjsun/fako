"""Rotas da partida: iniciar, pedir questão, responder e encerrar."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ml.classificador import ClassificadorClient, get_classificador
from app.models.user import User
from app.schemas.match_schema import (
    AnswerRequest,
    AnswerResultResponse,
    MatchResponse,
    MatchResultResponse,
    MatchStartRequest,
)
from app.schemas.question_schema import QuestionResponse
from app.services.match_service import MatchService

router = APIRouter(prefix="/matches", tags=["matches"])


def get_service(
    db: Session = Depends(get_db),
    classificador: ClassificadorClient = Depends(get_classificador),
) -> MatchService:
    return MatchService(db, classificador)


@router.post("", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
def start_match(
    data: MatchStartRequest,
    user: User = Depends(get_current_user),
    service: MatchService = Depends(get_service),
) -> MatchResponse:
    return service.start(user, data)


@router.get("/{match_id}", response_model=MatchResponse)
def get_match(
    match_id: int,
    user: User = Depends(get_current_user),
    service: MatchService = Depends(get_service),
) -> MatchResponse:
    return service.get(user, match_id)


@router.get("/{match_id}/next-question", response_model=QuestionResponse)
def next_question(
    match_id: int,
    user: User = Depends(get_current_user),
    service: MatchService = Depends(get_service),
) -> QuestionResponse:
    return service.next_question(user, match_id)


@router.post("/{match_id}/answers", response_model=AnswerResultResponse)
def answer(
    match_id: int,
    data: AnswerRequest,
    user: User = Depends(get_current_user),
    service: MatchService = Depends(get_service),
) -> AnswerResultResponse:
    return service.answer(user, match_id, data)


@router.post("/{match_id}/finish", response_model=MatchResultResponse)
def finish(
    match_id: int,
    user: User = Depends(get_current_user),
    service: MatchService = Depends(get_service),
) -> MatchResultResponse:
    return service.finish(user, match_id)
