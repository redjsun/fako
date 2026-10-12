"""Regras da partida: início, perguntas, respostas e encerramento."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.integrations.classificador_client import ClassificadorClient, FakeClassificador
from app.models.match import Match, MatchAnswer, MatchStatus
from app.models.question import QuestionStatus
from app.models.user import User
from app.repositories.level_repository import LevelRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.question_repository import QuestionRepository
from app.schemas.match_schema import (
    AnswerRequest,
    AnswerResultResponse,
    MatchResponse,
    MatchResultResponse,
    MatchStartRequest,
)
from app.schemas.question_schema import QuestionResponse
from app.services import game_rules
from app.services.classificador_service import ClassificadorService
from app.services.progress_service import ProgressService


class MatchService:
    def __init__(self, db: Session, classificador: ClassificadorClient | None = None) -> None:
        self.classificador = ClassificadorService(classificador or FakeClassificador())
        self.matches = MatchRepository(db)
        self.levels = LevelRepository(db)
        self.questions = QuestionRepository(db)
        self.progress = ProgressService(db)

    def start(self, user: User, data: MatchStartRequest) -> MatchResponse:
        progress = self.progress.get_or_create(user.id)
        number = data.level or progress.current_level
        if number > progress.highest_level:
            raise BusinessRuleError("Nível ainda não liberado para este jogador")

        level = self.levels.get_by_number(number)
        if level is None:
            raise NotFoundError("Nível não encontrado")

        match = self.matches.add(
            Match(
                user_id=user.id,
                level_id=level.id,
                duration_seconds=game_rules.MATCH_DURATION_SECONDS,
            )
        )
        return MatchResponse.model_validate(match)

    def get(self, user: User, match_id: int) -> MatchResponse:
        return MatchResponse.model_validate(self._get_match(user, match_id))

    def next_question(self, user: User, match_id: int) -> QuestionResponse:
        """Chamado pelo front quando a cobra come a maçã."""
        match = self._get_active_match(user, match_id)
        # TODO: filtrar as categorias liberadas para o nível da partida.
        question = self.questions.random_validated(
            exclude_ids=self.matches.answered_question_ids(match.id)
        )
        if question is None:
            raise NotFoundError("Não há mais questões disponíveis")
        return QuestionResponse(
            id=question.id, statement=question.statement, category=question.category.name
        )

    def answer(self, user: User, match_id: int, data: AnswerRequest) -> AnswerResultResponse:
        match = self._get_active_match(user, match_id)

        question = self.questions.get(data.question_id)
        if question is None or question.status != QuestionStatus.VALIDATED:
            raise NotFoundError("Questão não encontrada")
        if question.id in self.matches.answered_question_ids(match.id):
            raise BusinessRuleError("Questão já respondida nesta partida")

        is_correct = data.answer == question.is_true
        match.score += (
            game_rules.POINTS_PER_CORRECT_ANSWER
            if is_correct
            else game_rules.POINTS_PER_WRONG_ANSWER
        )
        self.matches.add_answer(
            MatchAnswer(
                match_id=match.id,
                question_id=question.id,
                answer=data.answer,
                is_correct=is_correct,
            )
        )
        # Feedback com a resposta certa e a explicação.
        return AnswerResultResponse(
            is_correct=is_correct,
            correct_answer=question.is_true,
            explanation=question.explanation,
            source=question.source,
            score=match.score,
            model_guess=self.classificador.palpite_do_jogo(question.statement),
        )

    def finish(self, user: User, match_id: int) -> MatchResultResponse:
        match = self._get_match(user, match_id)
        if match.status == MatchStatus.FINISHED:
            raise BusinessRuleError("Partida já encerrada")

        match.status = MatchStatus.FINISHED
        match.ended_at = datetime.now(timezone.utc)

        progress = self.progress.get_or_create(user.id)
        progress.total_score += match.score
        progress.matches_played += 1

        # Avança quando atinge a meta no nível atual e ainda há nível acima.
        advanced = (
            match.level.number == progress.current_level
            and match.score >= match.level.min_score_to_advance
            and progress.current_level < self.levels.max_number()
        )
        if advanced:
            progress.current_level += 1
            progress.highest_level = max(progress.highest_level, progress.current_level)

        return MatchResultResponse(
            match=MatchResponse.model_validate(match),
            advanced=advanced,
            current_level=progress.current_level,
        )

    def _get_match(self, user: User, match_id: int) -> Match:
        match = self.matches.get_for_user(match_id, user.id)
        if match is None:
            raise NotFoundError("Partida não encontrada")
        return match

    def _get_active_match(self, user: User, match_id: int) -> Match:
        match = self._get_match(user, match_id)
        if match.status != MatchStatus.IN_PROGRESS:
            raise BusinessRuleError("Partida já encerrada")

        # Depois dos 120 s não se aceita mais pergunta nem resposta.
        deadline = match.started_at + timedelta(
            seconds=match.duration_seconds + game_rules.ANSWER_GRACE_SECONDS
        )
        if datetime.now(timezone.utc) > deadline:
            raise BusinessRuleError("Tempo da partida esgotado")
        return match
