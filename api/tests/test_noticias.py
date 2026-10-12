import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.deps import get_current_admin
from app.integrations.classificador_client import FakeClassificador, get_classificador
from app.integrations.noticias_client import (
    FactCheckClient,
    GNewsClient,
    Noticia,
    NoticiasIndisponiveis,
    get_noticias_clients,
)
from app.main import app
from app.models.user import User


class NoticiasDeTeste:
    def __init__(self, noticias: list[Noticia]):
        self.noticias = noticias

    def buscar(self, quantidade: int) -> list[Noticia]:
        return self.noticias[:quantidade]


def noticia(titulo: str) -> Noticia:
    return Noticia(
        titulo=f"{titulo} - Jornal Teste",
        url=f"https://jornal.teste/{uuid.uuid4().hex}",
        veiculo="Jornal Teste",
        publicada_em=None,
    )


def checagem(alegacao: str, veredito: str, verdadeira: bool | None) -> Noticia:
    return Noticia(
        titulo=alegacao,
        url=f"https://agencia.teste/{uuid.uuid4().hex}",
        veiculo="Agência Teste",
        publicada_em=datetime(2026, 10, 3),
        veredito=veredito,
        verdadeira=verdadeira,
    )


@pytest.fixture
def admin_client(client: TestClient, monkeypatch):
    # Os padrões, independentes do .env de quem roda os testes.
    monkeypatch.setenv("NOTICIAS_PUBLICAR_DIRETO", "false")
    monkeypatch.setenv("NOTICIAS_SEM_POLITICA", "false")
    get_settings.cache_clear()
    app.dependency_overrides[get_current_admin] = lambda: User(
        id=1, username="admin", is_admin=True
    )
    app.dependency_overrides[get_classificador] = FakeClassificador
    yield client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_importa_noticias_como_rascunho_normalizado_com_analise(admin_client: TestClient):
    marca = uuid.uuid4().hex[:6]
    manchete = f"Prefeitura abre {marca} vagas em creches municipais"
    noticias = [
        noticia(manchete),
        noticia(f"Ministro diz que vai abrir {marca} vagas"),
        noticia(manchete),  # repetida no mesmo lote
    ]
    app.dependency_overrides[get_noticias_clients] = lambda: [NoticiasDeTeste(noticias)]

    resposta = admin_client.post("/admin/news/import", json={"category": "saude", "quantity": 3})

    assert resposta.status_code == 201
    corpo = resposta.json()
    [importada] = corpo["imported"]
    assert importada["statement"] == manchete
    assert importada["status"] == "draft" and importada["origin"] == "news"
    assert importada["is_true"] is True
    assert importada["explanation"] == "Manchete publicada por Jornal Teste."
    assert importada["model_version"] == "fake" and importada["model_category"]
    assert [d["reason"] for d in corpo["discarded"]] == ["relata fala", "já importada"]

    # De novo: a mesma manchete já está no banco.
    resposta = admin_client.post("/admin/news/import", json={"category": "saude", "quantity": 1})
    assert resposta.json()["imported"] == []


def test_importa_checagens_com_o_lado_do_veredito(admin_client: TestClient):
    marca = uuid.uuid4().hex[:6]
    checagens = [
        # Pergunta e fala relatada fazem parte do boato: não caem nos filtros de portal.
        checagem(f"Médico diz que vacina {marca} altera o DNA?", "falso", False),
        checagem(f"Governo distribuiu {marca} cestas básicas em outubro", "verdadeiro", True),
        checagem(f"Imposto sobre {marca} subiu 300% neste ano", "exagerado", None),
    ]
    app.dependency_overrides[get_noticias_clients] = lambda: [NoticiasDeTeste(checagens)]

    resposta = admin_client.post("/admin/news/import", json={"quantity": 3})

    assert resposta.status_code == 201
    corpo = resposta.json()
    falsa, verdadeira = corpo["imported"]
    assert falsa["is_true"] is False and verdadeira["is_true"] is True
    assert falsa["explanation"] == "Checado por Agência Teste em 03/10/2026: falso."
    assert falsa["category"] == "conhecimentos-gerais"
    assert [d["reason"] for d in corpo["discarded"]] == ["veredito sem lado no jogo (exagerado)"]


class ProvedorFora:
    def buscar(self, quantidade: int) -> list[Noticia]:
        raise NoticiasIndisponiveis("fora do ar")


def test_divide_a_quantidade_entre_os_provedores(admin_client: TestClient, monkeypatch):
    monkeypatch.setenv("NOTICIAS_PUBLICAR_DIRETO", "true")
    get_settings.cache_clear()
    marca = uuid.uuid4().hex[:6]
    checagens = [
        checagem(f"Chá de {marca} cura a dengue em {i} dias", "falso", False) for i in range(3)
    ]
    manchetes = [
        noticia(f"Prefeitura inaugura {marca} unidades de saúde no bairro {i}") for i in range(3)
    ]
    app.dependency_overrides[get_noticias_clients] = lambda: [
        NoticiasDeTeste(checagens),
        ProvedorFora(),  # um provedor fora do ar não derruba os outros
        NoticiasDeTeste(manchetes),
    ]
    try:
        corpo = admin_client.post("/admin/news/import", json={"quantity": 4}).json()
    finally:
        get_settings.cache_clear()
    importadas = corpo["imported"]
    # 4 em 3 provedores: 2 + 1 (fora do ar, não importa) + 2 (o que sobrou).
    assert [q["is_true"] for q in importadas] == [False, False, True, True]
    assert all(q["status"] == "validated" and q["validated_at"] for q in importadas)


def test_todos_os_provedores_fora_responde_indisponivel(admin_client: TestClient):
    app.dependency_overrides[get_noticias_clients] = lambda: [ProvedorFora(), ProvedorFora()]
    assert admin_client.post("/admin/news/import", json={}).status_code == 503


def test_factcheck_sem_chave_responde_indisponivel(admin_client: TestClient, monkeypatch):
    monkeypatch.setenv("NOTICIAS_PROVIDER", "factcheck")
    monkeypatch.setenv("FACTCHECK_API_KEY", "")
    get_settings.cache_clear()
    try:
        resposta = admin_client.post("/admin/news/import", json={})
        assert resposta.status_code == 503
    finally:
        get_settings.cache_clear()


def test_factcheck_converte_alegacao_com_a_checagem_da_agencia_pedida():
    claim = {
        "text": "Vacina contém chip",
        "claimReview": [
            {"publisher": {"name": "Outra", "site": "outra.org"}, "textualRating": "Verdadeiro"},
            {
                "publisher": {"name": "Aos Fatos", "site": "aosfatos.org"},
                "url": "https://aosfatos.org/x",
                "reviewDate": "2026-10-03T00:00:00Z",
                "textualRating": "Falso",
            },
        ],
    }
    convertida = FactCheckClient.checagem(claim, "aosfatos.org")
    assert convertida.veiculo == "Aos Fatos" and convertida.url == "https://aosfatos.org/x"
    assert convertida.veredito == "falso" and convertida.verdadeira is False
    assert FactCheckClient.checagem({"text": "sem checagem"}, "aosfatos.org") is None


def test_gnews_sem_chave_responde_indisponivel(admin_client: TestClient, monkeypatch):
    monkeypatch.setenv("NOTICIAS_PROVIDER", "gnews")
    monkeypatch.setenv("NOTICIAS_API_KEY", "")
    get_settings.cache_clear()
    try:
        resposta = admin_client.post("/admin/news/import", json={"category": "saude"})
        assert resposta.status_code == 503
    finally:
        get_settings.cache_clear()


def test_gnews_intercala_os_topicos(monkeypatch):
    cliente = GNewsClient("chave")
    pedidos = []

    def do_topico(topico, quantidade):
        pedidos.append(topico)
        return [noticia(f"{topico} {i}") for i in range(2)]

    monkeypatch.setattr(cliente, "do_topico", do_topico)
    monkeypatch.setattr(cliente, "PAUSA", 0)
    titulos = [n.titulo.split(" - ")[0] for n in cliente.buscar(4)]
    assert pedidos == ["health", "science", "technology"]
    assert titulos == ["health 0", "science 0", "technology 0", "health 1"]


def test_gnews_converte_artigo():
    artigo = {
        "title": "Título",
        "url": "https://x.com/a",
        "publishedAt": "2026-10-10T12:00:00Z",
        "source": {"name": "Veículo"},
    }
    convertida = GNewsClient.noticia(artigo)
    assert convertida.veiculo == "Veículo" and convertida.publicada_em.year == 2026


def test_analise_do_classificador_para_o_admin(admin_client: TestClient):
    resposta = admin_client.post(
        "/admin/classifier/analyze", json={"statement": "Vacina tem chip | G1"}
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["normalized_statement"] == "Vacina tem chip"
    assert corpo["model_version"] == "fake"


def test_palpite_do_modelo_no_feedback_da_resposta(
    client: TestClient, auth_headers: dict[str, str], monkeypatch
):
    monkeypatch.setenv("CLASSIFICADOR_NO_JOGO", "true")
    get_settings.cache_clear()
    app.dependency_overrides[get_classificador] = FakeClassificador
    try:
        partida = client.post("/matches", json={}, headers=auth_headers).json()
        questao = client.get(f"/matches/{partida['id']}/next-question", headers=auth_headers)
        resposta = client.post(
            f"/matches/{partida['id']}/answers",
            json={"question_id": questao.json()["id"], "answer": True},
            headers=auth_headers,
        )
        palpite = resposta.json()["model_guess"]
        assert palpite["model_version"] == "fake"
        assert palpite["category"] == "incerto"  # o fake fica abaixo do limiar do jogador
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
