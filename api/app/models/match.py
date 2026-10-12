"""Partida do jogador e respostas dadas nela."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Entity, enum_values
from app.models.level import Level


class MatchStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class Match(Entity):
    __tablename__ = "matches"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"))
    score: Mapped[int] = mapped_column(Integer, default=0)
    # Duração máxima de 120 segundos.
    duration_seconds: Mapped[int] = mapped_column(Integer, default=120)
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, native_enum=False, length=20, values_callable=enum_values),
        default=MatchStatus.IN_PROGRESS,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Pergunta servida e ainda sem resposta: a única que a partida aceita responder.
    current_question_id: Mapped[int | None] = mapped_column(
        ForeignKey("questions.id"), nullable=True
    )

    level: Mapped[Level] = relationship()
    answers: Mapped[list["MatchAnswer"]] = relationship(back_populates="match")


class MatchAnswer(Entity):
    """Confiabilidade (0 a 100) dada pelo jogador a uma questão durante a partida."""

    __tablename__ = "match_answers"

    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    # Leitura binária da resposta (confiabilidade >= 50), mantida para relatórios.
    answer: Mapped[bool] = mapped_column(Boolean)
    reliability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean)

    match: Mapped[Match] = relationship(back_populates="answers")
