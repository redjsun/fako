import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_admin
from app.integrations.classificador_client import ClassificadorAusente, get_classificador
from app.integrations.llm_client import (
    VERSAO_PROMPT,
    ChecagemDeOrigem,
    FakeLLMClient,
    LLMValidado,
    QuestaoGerada,
    RespostaInvalida,
    get_llm_client,
)
from app.integrations.noticias_client import get_noticias_clients
from app.main import app
from app.models.user import User
from tests.test_ai_clients import PedidoRoteirizado
from tests.test_noticias import NoticiasDeTeste, checagem


def unica(alegacao: str) -> str:
    """O banco de teste guarda as questões entre execuções; a deduplicação compara o texto."""
    return f"{alegacao} no lote {uuid.uuid4().hex[:6]}"


class LLMQueReescreve(FakeLLMClient):
    """Reescreve como "Reescrita: ..." e falha nas alegações com "quebrada"."""

    def gerar_questao(self, origem: ChecagemDeOrigem) -> QuestaoGerada:
        if "quebrada" in origem.alegacao:
            raise RespostaInvalida("fora do esquema")
        return QuestaoGerada(f"Reescrita: {origem.alegacao}", None, VERSAO_PROMPT["gerar_questao"])


@pytest.fixture
def admin_client(client: TestClient):
    app.dependency_overrides[get_current_admin] = lambda: User(
        id=1, username="admin", is_admin=True
    )
    return client


def test_gera_rascunhos_com_o_gabarito_e_a_fonte_da_checagem(admin_client: TestClient):
    falsa = checagem(unica("Chá de boldo cura a dengue em um dia"), "Falso", False)
    verdadeira = checagem(
        unica("Ministério ampliou a vacinação contra a gripe"), "Verdadeiro", True
    )
    checagens = [
        falsa,
        checagem(unica("Alegação quebrada pela LLM sobre vacinas"), "Falso", False),
        checagem(unica("Vacina causa efeito raro em parte dos casos"), "Enganoso", None),
        verdadeira,
    ]
    app.dependency_overrides[get_noticias_clients] = lambda: [NoticiasDeTeste(checagens)]
    app.dependency_overrides[get_llm_client] = LLMQueReescreve

    resposta = admin_client.post("/admin/ai/generate", json={"category": "saude", "quantity": 5})

    assert resposta.status_code == 201
    geradas = resposta.json()
    assert [q["statement"] for q in geradas] == [
        f"Reescrita: {falsa.titulo}",
        f"Reescrita: {verdadeira.titulo}",
    ]
    assert [q["is_true"] for q in geradas] == [False, True]
    assert [q["source"] for q in geradas] == [falsa.url, verdadeira.url]
    assert all(q["status"] == "draft" and q["origin"] == "ai" for q in geradas)

    # A mesma checagem não vira questão duas vezes.
    resposta = admin_client.post("/admin/ai/generate", json={"category": "saude", "quantity": 5})
    assert resposta.json() == []


def test_classify_mantem_o_formato_com_o_classificador(admin_client: TestClient):
    resposta = admin_client.post("/admin/ai/classify", json={"statement": "A terra é plana"})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert set(corpo) == {"suggested_is_true", "confidence", "rationale"}
    assert corpo["suggested_is_true"] is False  # o fake classifica como falso
    assert "fake" in corpo["rationale"]


def test_classify_sem_modelo_responde_503(admin_client: TestClient):
    app.dependency_overrides[get_classificador] = lambda: ClassificadorAusente("sem modelo")
    resposta = admin_client.post("/admin/ai/classify", json={"statement": "A terra é plana"})
    assert resposta.status_code == 503
    assert "Análise indisponível" in resposta.json()["detail"]


@pytest.mark.parametrize("rota", ["/admin/ai/generate", "/admin/ai/classify"])
def test_jogador_comum_recebe_403(client: TestClient, auth_headers, rota):
    corpo = {"category": "saude", "statement": "A terra é plana"}
    resposta = client.post(rota, json=corpo, headers=auth_headers)
    assert resposta.status_code == 403


def test_gabarito_e_fonte_nunca_vem_da_llm(admin_client: TestClient):
    falsa = checagem(unica("Chá de boldo cura a dengue em um dia"), "Falso", False)
    app.dependency_overrides[get_noticias_clients] = lambda: [NoticiasDeTeste([falsa])]
    # A LLM tenta dar o gabarito e a fonte: os campos fora do esquema são ignorados.
    resposta_llm = (
        f'{{"statement": "{falsa.titulo}", "category": "saude", '
        '"is_true": true, "source": "https://inventado.teste"}'
    )
    app.dependency_overrides[get_llm_client] = lambda: LLMValidado(PedidoRoteirizado(resposta_llm))

    [gerada] = admin_client.post(
        "/admin/ai/generate", json={"category": "saude", "quantity": 1}
    ).json()

    assert gerada["is_true"] is False
    assert gerada["source"] == falsa.url


@pytest.mark.parametrize(
    "reescrita",
    [
        "O governo vai confiscar a poupança dos brasileiros",  # troca de assunto
        "Chá de boldo não cura a dengue em um dia",  # inversão de sentido
    ],
)
def test_reescrita_infiel_e_descartada(admin_client: TestClient, reescrita):
    falsa = checagem(unica("Chá de boldo cura a dengue em um dia"), "Falso", False)
    app.dependency_overrides[get_noticias_clients] = lambda: [NoticiasDeTeste([falsa])]
    resposta_llm = f'{{"statement": "{reescrita}", "category": "saude"}}'
    app.dependency_overrides[get_llm_client] = lambda: LLMValidado(PedidoRoteirizado(resposta_llm))

    resposta = admin_client.post("/admin/ai/generate", json={"category": "saude", "quantity": 1})

    assert resposta.status_code == 201 and resposta.json() == []
