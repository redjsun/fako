"""Regras de pontuação e tempo da partida comuns a todos os níveis.

O que muda de um nível para outro (duração, tolerância, penalidade do erro...) fica na
tabela `levels` (app/models/level.py).
"""

# O cronômetro da partida fica no front e pausa durante a pergunta, o feedback e as pausas,
# então o servidor não mede o tempo de jogo: só recusa partidas abertas há mais que isto.
MATCH_MAX_OPEN_SECONDS = 30 * 60
# Teto de respostas por partida (uma a cada 2 s da partida mais longa), já que o servidor
# não mede o tempo de jogo: limita o placar de quem chama a API direto, sem pesar para quem joga.
MAX_ANSWERS_PER_MATCH = 60

POINTS_PER_CORRECT_ANSWER = 10


def default_reliability_reference(is_true: bool) -> int:
    """Referência para questões cadastradas sem uma confiabilidade própria."""
    return 90 if is_true else 10


def is_within_tolerance(reliability: int, reference: int, tolerance: int) -> bool:
    return abs(reliability - reference) <= tolerance


def score_after_answer(score: int, is_correct: bool, wrong_answer_penalty: int) -> int:
    """Placar depois de uma resposta; o erro tira pontos, mas o placar nunca fica negativo."""
    if is_correct:
        return score + POINTS_PER_CORRECT_ANSWER
    return max(0, score - wrong_answer_penalty)
