import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.deps import get_current_admin
from app.integrations.classificador_client import FakeClassificador, get_classificador
from app.integrations.noticias_client import GNewsClient, Noticia, get_noticias_client
from app.main import app
from app.models.user import User


class NoticiasDeTeste:
    def __init__(self, noticias: list[Noticia]):
        self.noticias = noticias

    def buscar(self, categoria: str, quantidade: int) -> list[Noticia]:
        return self.noticias[:quantidade]


def noticia(titulo: str) -> Noticia:
    return Noticia(
        titulo=f"{titulo} - Jornal Teste",
        url=f"https://jornal.teste/{uuid.uuid4().hex}",
        veiculo="Jornal Teste",
        publicada_em=None,
    )


@pytest.fixture
def admin_client(client: TestClient):
    app.dependency_overrides[get_current_admin] = lambda: User(
        id=1, username="admin", is_admin=True
    )
    app.dependency_overrides[get_classificador] = FakeClassificador
    yield client
    app.dependency_overrides.clear()


def test_importa_noticias_como_rascunho_normalizado_com_analise(admin_client: TestClient):
    marca = uuid.uuid4().hex[:6]
    manchete = f"Prefeitura abre {marca} vagas em creches municipais"
    noticias = [
        noticia(manchete),
        noticia(f"Ministro diz que vai abrir {marca} vagas"),
        noticia(manchete),  # repetida no mesmo lote
    ]
    app.dependency_overrides[get_noticias_client] = lambda: NoticiasDeTeste(noticias)

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


def test_gnews_sem_chave_responde_indisponivel(admin_client: TestClient, monkeypatch):
    monkeypatch.setenv("NOTICIAS_PROVIDER", "gnews")
    monkeypatch.setenv("NOTICIAS_API_KEY", "")
    get_settings.cache_clear()
    try:
        resposta = admin_client.post("/admin/news/import", json={"category": "saude"})
        assert resposta.status_code == 503
    finally:
        get_settings.cache_clear()


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
