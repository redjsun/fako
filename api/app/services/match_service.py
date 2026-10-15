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
                duration_seconds=level.match_seconds,
            )
        )
        return MatchResponse.model_validate(match)

    def get(self, user: User, match_id: int) -> MatchResponse:
        return MatchResponse.model_validate(self._get_match(user, match_id))

    def next_question(self, user: User, match_id: int) -> QuestionResponse:
        """Chamado pelo front quando a cobra come a maçã."""
        match = self._get_active_match(user, match_id)
        # Enquanto a pergunta servida não é respondida, ela é devolvida de novo: sortear outra
        # deixaria escolher só as afirmações cuja referência o jogador já conhece.
        question = (
            self.questions.get(match.current_question_id) if match.current_question_id else None
        )
        if question is None:
            answered = self.matches.answered_question_ids(match.id)
            if len(answered) >= game_rules.MAX_ANSWERS_PER_MATCH:
                raise BusinessRuleError("Limite de respostas da partida atingido")
            # TODO: filtrar as categorias liberadas para o nível da partida.
            question = self.questions.random_validated(exclude_ids=answered)
            if question is None:
                raise NotFoundError("Não há mais questões disponíveis")
            match.current_question_id = question.id
        return QuestionResponse(
            id=question.id, statement=question.statement, category=question.category.name
        )

    def answer(self, user: User, match_id: int, data: AnswerRequest) -> AnswerResultResponse:
        match = self._get_active_match(user, match_id)
        # Só a pergunta servida e pendente; isso também impede responder a mesma duas vezes.
        if data.question_id != match.current_question_id:
            raise BusinessRuleError("Questão não é a pergunta atual desta partida")

        question = self.questions.get(data.question_id)
        if question is None or question.status != QuestionStatus.VALIDATED:
            raise NotFoundError("Questão não encontrada")
        match.current_question_id = None

        level = match.level
        is_correct = game_rules.is_within_tolerance(
            data.reliability, question.reliability_reference, level.reliability_tolerance
        )
        match.score = game_rules.score_after_answer(
            match.score, is_correct, level.wrong_answer_penalty
        )
        self.matches.add_answer(
            MatchAnswer(
                match_id=match.id,
                question_id=question.id,
                answer=data.reliability >= 50,
                reliability=data.reliability,
                is_correct=is_correct,
            )
        )
        # Feedback com a resposta certa e a explicação.
        return AnswerResultResponse(
            is_correct=is_correct,
            correct_answer=question.is_true,
            reliability=data.reliability,
            reliability_reference=question.reliability_reference,
            tolerance=level.reliability_tolerance,
            distance=abs(data.reliability - question.reliability_reference),
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

        # O tempo de jogo é controlado no front; aqui só o teto de partida aberta.
        deadline = match.started_at + timedelta(seconds=game_rules.MATCH_MAX_OPEN_SECONDS)
        if datetime.now(timezone.utc) > deadline:
            raise BusinessRuleError("Tempo da partida esgotado")
        return match
