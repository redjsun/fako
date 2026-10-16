"""Regras da partida: início, perguntas, respostas e encerramento."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.ml.classificador import ClassificadorClient, FakeClassificador
from app.models.match import Match, MatchAnswer, MatchStatus
from app.models.question import Question, QuestionStatus
from app.models.user import User
from app.repositories.level_repository import LevelRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.question_repository import QuestionRepository
from app.schemas.match_schema import (
    AnswerRequest,
    AnswerResultResponse,
    ClaimOriginResponse,
    MatchResponse,
    MatchResultResponse,
    MatchStartRequest,
)
from app.schemas.question_schema import QuestionResponse
from app.services import game_rules
from app.services.classificador_service import ClassificadorService
from app.services.progress_service import ProgressService


def origem_da_afirmacao(question: Question) -> ClaimOriginResponse | None:
    if not question.origin_author:
        return None  # questões humanas e as importadas antes da origem
    return ClaimOriginResponse(
        kind="materia" if question.origin_link else "alegacao",
        author=question.origin_author,
        when=question.origin_date,
        link=question.origin_link,
    )


class MatchService:
    def __init__(self, db: Session, classificador: ClassificadorClient | None = None) -> None:
        self.classificador = ClassificadorService(classificador or FakeClassificador())
        self.matches = MatchRepository(db)
        self.levels = LevelRepository(db)
        self.questions = QuestionRepository(db)
        self.progress = ProgressService(db)

    def start(self, user: User, data: MatchStartRequest) -> MatchResponse:
        progress = self.progress.get_or_create(user.id)
        number = data.level if data.level is not None else progress.current_level
        if number > progress.highest_level:
            raise BusinessRuleError("Nível ainda não liberado para este jogador")

        level = self.levels.get_by_number(number)
        if level is None:
            raise NotFoundError("Nível não encontrado")

        # Uma partida aberta por jogador: a que ficou no meio (aba fechada, saída sem encerrar)
        # é abandonada, sem contar pontos. Assim ninguém junta partidas abertas para escolher
        # depois quais encerrar.
        self.matches.abandon_in_progress(user.id, datetime.now(timezone.utc))
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
        if question is not None and question.status != QuestionStatus.VALIDATED:
            # Despublicada depois de servida: sai da partida, senão ela voltaria para sempre
            # sem poder ser respondida.
            question = None
        if question is None:
            answered = self.matches.answered_question_ids(match.id)
            if len(answered) >= game_rules.MAX_ANSWERS_PER_MATCH:
                raise BusinessRuleError("Limite de respostas da partida atingido")
            # TODO: filtrar as categorias liberadas para o nível da partida.
            question = self.questions.random_validated(exclude_ids=answered)
            if question is None:
                raise NotFoundError("Não há mais questões disponíveis")
            match.current_question_id = question.id
            # A pergunta reenviada mantém a hora da primeira vez: pedir de novo não dá mais tempo.
            match.current_question_served_at = datetime.now(timezone.utc)
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

        level = match.level
        served_at = match.current_question_served_at
        timed_out = served_at is not None and datetime.now(timezone.utc) > served_at + timedelta(
            seconds=game_rules.question_deadline_seconds(level.question_seconds)
        )
        match.current_question_id = None
        match.current_question_served_at = None

        # Fora do tempo vale como erro, qualquer que seja a confiabilidade marcada.
        is_correct = not timed_out and game_rules.is_within_tolerance(
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
            explanation=self.explicacao(question),
            source=question.source,
            score=match.score,
            timed_out=timed_out,
            model_guess=self.classificador.palpite_do_jogo(question.statement, question.claim_text),
            claim_origin=origem_da_afirmacao(question),
        )

    def explicacao(self, question) -> str:
        """O "Por quê?": a explicação da LLM sobre a avaliação do classificador, se foi feita
        pelo modelo publicado (a avaliação que o jogador vê); senão, a explicação da fonte."""
        if not get_settings().classificador_no_jogo:
            return question.explanation
        versao = getattr(self.classificador.classificador, "versao", None)
        if question.model_explanation and question.model_version == versao:
            return question.model_explanation
        return question.explanation

    def finish(self, user: User, match_id: int) -> MatchResultResponse:
        # Mesma regra das respostas: partida aberta há mais que o teto não conta mais (nem
        # pontos nem avanço) e fica aberta até o jogador começar outra, que a abandona.
        match = self._get_active_match(user, match_id)

        match.status = MatchStatus.FINISHED
        match.ended_at = datetime.now(timezone.utc)

        progress = self.progress.get_or_create(user.id, bloquear=True)
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

    def _get_match(self, user: User, match_id: int, bloquear: bool = False) -> Match:
        match = self.matches.get_for_user(match_id, user.id, bloquear)
        if match is None:
            raise NotFoundError("Partida não encontrada")
        return match

    def _get_active_match(self, user: User, match_id: int) -> Match:
        """A partida que vai mudar (pergunta, resposta, encerramento), travada até o commit:
        pedidos simultâneos são atendidos um de cada vez e o segundo já vê o que o primeiro
        gravou (a pergunta respondida, a partida encerrada)."""
        match = self._get_match(user, match_id, bloquear=True)
        if match.status != MatchStatus.IN_PROGRESS:
            raise ConflictError("Partida já encerrada")

        # O tempo de jogo é controlado no front; aqui só o teto de partida aberta.
        deadline = match.started_at + timedelta(seconds=game_rules.MATCH_MAX_OPEN_SECONDS)
        if datetime.now(timezone.utc) > deadline:
            raise BusinessRuleError("Tempo da partida esgotado")
        return match
