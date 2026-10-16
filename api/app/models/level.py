"""Nível de dificuldade da partida."""

from sqlalchemy import Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Entity


class Level(Entity):
    """Regras de um nível da jornada; a tabela completa está em doc/jogo/niveis.md."""

    __tablename__ = "levels"

    number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    # Lado do tabuleiro, em células.
    board_size: Mapped[int] = mapped_column(Integer)
    # Intervalo entre movimentos da cobra; menor = mais difícil.
    tick_ms: Mapped[int] = mapped_column(Integer)
    # Pontuação mínima na partida para liberar o próximo nível.
    min_score_to_advance: Mapped[int] = mapped_column(Integer)
    # Tempo de cobra andando na partida e tempo para responder cada pergunta.
    match_seconds: Mapped[int] = mapped_column(Integer)
    question_seconds: Mapped[int] = mapped_column(Integer)
    # A resposta acerta quando fica a até esta distância da confiabilidade de referência.
    reliability_tolerance: Mapped[int] = mapped_column(Integer)
    # Pontos tirados a cada erro (o placar nunca fica negativo) e blocos que a cobra cresce.
    wrong_answer_penalty: Mapped[int] = mapped_column(Integer)
    growth_per_error: Mapped[int] = mapped_column(Integer)
    # Mecânica do tabuleiro, aplicada no front: paredes que matam em vez de atravessar,
    # maçã que muda de lugar depois de um tempo e maçãs podres a evitar.
    solid_walls: Mapped[bool] = mapped_column(Boolean)
    apple_lifetime_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rotten_apples: Mapped[int] = mapped_column(Integer)
