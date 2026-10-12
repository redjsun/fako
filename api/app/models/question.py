"""Questão do banco de conteúdo, com a confiabilidade de referência da afirmação."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Entity, enum_values
from app.models.category import Category


class QuestionStatus(str, enum.Enum):
    """Só questões `validated` chegam ao jogador."""

    DRAFT = "draft"
    VALIDATED = "validated"
    REJECTED = "rejected"


class QuestionOrigin(str, enum.Enum):
    HUMAN = "human"
    AI = "ai"
    NEWS = "news"  # manchete de notícia externa (services/noticias_service.py)


class Question(Entity):
    __tablename__ = "questions"

    statement: Mapped[str] = mapped_column(Text)
    is_true: Mapped[bool] = mapped_column(Boolean)
    # Confiabilidade de referência (0 a 100) usada na barra do jogo.
    reliability_reference: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(Text)
    # Origem da informação usada na validação.
    source: Mapped[str] = mapped_column(String(500))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    status: Mapped[QuestionStatus] = mapped_column(
        Enum(QuestionStatus, native_enum=False, length=20, values_callable=enum_values),
        default=QuestionStatus.DRAFT,
        index=True,
    )
    origin: Mapped[QuestionOrigin] = mapped_column(
        Enum(QuestionOrigin, native_enum=False, length=20, values_callable=enum_values),
        default=QuestionOrigin.HUMAN,
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Análise do classificador na curadoria (limiar do admin), para apoiar a revisão humana.
    model_category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    model_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    category: Mapped[Category] = relationship()
