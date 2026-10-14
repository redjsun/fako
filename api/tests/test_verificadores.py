import json

import pytest

from app.integrations.embeddings_client import FakeEmbeddings, cosseno
from app.integrations.verificadores import (
    citados,
    verificar_explicacao,
    verificar_negacao,
    verificar_reescrita,
)

ENTRADA = json.dumps(
    {
        "afirmacao": "O Ministério da Saúde proibiu a vacina em 2021",
        "categoria": "falso",
        "checagem_parecida": {
            "alegacao": "...",
            "veredito": "falso",
            "url": "https://lupa.teste/1",
        },
    },
    ensure_ascii=False,
)


def test_explicacao_so_com_o_que_esta_na_analise_passa():
    explicacao = (
        "É muito parecida com uma checagem da https://lupa.teste/1 que concluiu que é falso. "
        "O texto diz que o Ministério da Saude proibiu a vacina em 2021."
    )
    assert verificar_explicacao(explicacao, ENTRADA, "falso") is None


@pytest.mark.parametrize(
    "explicacao, inventado",
    [
        ("A OMS já desmentiu essa afirmação.", "OMS"),
        ("O boato circulou por 30 dias antes de ser checado.", "30"),
        ("Segundo o Instituto Butantan, isso não acontece.", "Instituto Butantan"),
        ("Veja mais em www.boatos.org/vacina.", "www.boatos.org/vacina."),
    ],
)
def test_explicacao_com_fato_novo_e_recusada(explicacao, inventado):
    motivo = verificar_explicacao(explicacao, ENTRADA, "falso")
    assert motivo and inventado in motivo


def test_primeira_palavra_da_frase_nao_conta_como_nome():
    assert citados("Esta afirmação é falsa. Também pede que você compartilhe.") == set()


def test_incerto_precisa_dizer_que_o_modelo_nao_tem_certeza():
    assert verificar_explicacao("O texto usa urgência.", ENTRADA, "incerto")
    assert verificar_explicacao("O modelo não tem certeza sobre isso.", ENTRADA, "incerto") is None


def test_reescrita_com_outro_assunto_e_recusada():
    embeddings = FakeEmbeddings()
    original = "Vacina da gripe causa paralisia em idosos"
    assert (
        verificar_reescrita(
            original, "A vacina da gripe causa paralisia em idosos", embeddings, 0.6
        )
        is None
    )
    assert verificar_reescrita(original, "O governo vai confiscar a poupança", embeddings, 0.6)


def test_negacao_a_mais_ou_a_menos_e_recusada():
    assert verificar_negacao(
        "Soldado não atirou contra policiais", "Soldado atirou contra policiais"
    )
    assert verificar_negacao("Soldado atirou", "Soldado nunca atirou")
    assert verificar_negacao("Não há vacina", "Nenhuma vacina existe") is None


def test_cosseno():
    assert cosseno([1, 0], [1, 0]) == pytest.approx(1)
    assert cosseno([1, 0], [0, 1]) == pytest.approx(0)
    assert cosseno([0, 0], [1, 0]) == 0
