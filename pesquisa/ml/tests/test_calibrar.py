import numpy as np
import pytest

from avaliar import ece, probabilidades
from calibrar import (
    SEM_DECISAO,
    aplicar,
    calibrar,
    deslocar_proporcao,
    limiares,
    taxa_verdadeiro_vira_falso,
)


def exemplo_superconfiante(n: int = 3000, semente: int = 0):
    """Fronteiras verdadeiras conhecidas, e um modelo que exagera a confiança (logit × 3)."""
    gerador = np.random.default_rng(semente)
    q1 = gerador.uniform(0.05, 0.95, n)
    q2 = q1 * gerador.uniform(0.1, 0.9, n)
    sorteio = gerador.uniform(size=n)
    y = np.where(sorteio < 1 - q1, 0, np.where(sorteio < 1 - q2, 1, 2))

    def exagerar(p):
        return 1 / (1 + np.exp(-3 * np.log(p / (1 - p))))

    return exagerar(q1), np.minimum(exagerar(q2), exagerar(q1)), y


def test_platt_reduz_o_erro_de_calibracao_e_mantem_p1_maior_que_p2():
    p1, p2, y = exemplo_superconfiante()
    calibracao = calibrar(p1, p2, y)
    c1, c2 = aplicar(p1, p2, calibracao)
    assert ece(probabilidades(c1, c2), y)[0] < ece(probabilidades(p1, p2), y)[0]
    assert np.all(c1 >= c2)
    assert calibracao["fronteira_1"]["a"] == pytest.approx(1 / 3, abs=0.1)


def test_limiares_respeitam_as_taxas_de_verdadeiro_que_vira_falso():
    p1, p2, y = exemplo_superconfiante(semente=1)
    proba = probabilidades(*aplicar(p1, p2, calibrar(p1, p2, y)))
    escolhidos = limiares(proba, y)
    assert taxa_verdadeiro_vira_falso(proba, y, escolhidos["admin"]) <= 0.05
    assert taxa_verdadeiro_vira_falso(proba, y, escolhidos["jogador"]) <= 0.01
    assert escolhidos["jogador"] >= escolhidos["admin"]


def test_sem_limiar_possivel_tudo_vira_incerto():
    # O único verdadeiro é previsto como falso com toda a confiança.
    proba = np.array([[1.0, 0.0, 0.0], [0.9, 0.05, 0.05]])
    assert limiares(proba, np.array([2, 0]), {"jogador": 0.0}) == {"jogador": SEM_DECISAO}


def test_proporcao_do_jogo_desloca_so_o_vies_e_aumenta_os_verdadeiros():
    p1, p2, y = exemplo_superconfiante(semente=2)
    raros = (y < 2) | (np.arange(len(y)) % 10 == 0)  # verdadeiros raros, como na validação
    p1, p2, y = p1[raros], p2[raros], y[raros]
    calibracao = calibrar(p1, p2, y)
    deslocada = deslocar_proporcao(calibracao, y, 0.5)
    for fronteira in ("fronteira_1", "fronteira_2"):
        assert deslocada[fronteira]["a"] == calibracao[fronteira]["a"]
    assert deslocada["fronteira_2"]["b"] > calibracao["fronteira_2"]["b"]
    assert deslocada["proporcao"]["validacao"]["fronteira_2"] == pytest.approx(np.mean(y == 2))
    _, antes = aplicar(p1, p2, calibracao)
    c1, depois = aplicar(p1, p2, deslocada)
    assert np.mean(depois > 0.5) > np.mean(antes > 0.5)
    assert np.all(c1 >= depois)


def test_proporcao_igual_a_da_validacao_nao_muda_nada():
    p1, p2, y = exemplo_superconfiante(semente=3)
    calibracao = calibrar(p1, p2, y)
    deslocada = deslocar_proporcao(calibracao, y, float(np.mean(y > 1)))
    assert deslocada["fronteira_2"]["b"] == pytest.approx(calibracao["fronteira_2"]["b"])
