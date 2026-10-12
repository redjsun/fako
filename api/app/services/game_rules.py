"""Regras de pontuação e tempo da partida.

Valores iniciais para o MVP; ajuste aqui quando o grupo fechar as regras.
"""

MATCH_DURATION_SECONDS = 120
# O cronômetro de 120 s fica no front e pausa durante a pergunta, o feedback e as pausas,
# então o servidor não mede o tempo de jogo: só recusa partidas abertas há mais que isto.
MATCH_MAX_OPEN_SECONDS = 30 * 60

POINTS_PER_CORRECT_ANSWER = 10
# Consequência do erro na pontuação. A consequência na mecânica
# (ex.: a cobra diminuir) fica no front, em web/src/game.
POINTS_PER_WRONG_ANSWER = 0

# A resposta acerta quando fica a até esta distância da confiabilidade de referência.
RELIABILITY_TOLERANCE = 15


def default_reliability_reference(is_true: bool) -> int:
    """Referência para questões cadastradas sem uma confiabilidade própria."""
    return 90 if is_true else 10


def is_within_tolerance(reliability: int, reference: int) -> bool:
    return abs(reliability - reference) <= RELIABILITY_TOLERANCE
