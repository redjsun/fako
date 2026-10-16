"""Concorrência, tempo da pergunta, limite de login e segredo do JWT."""

import threading
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import SEGREDO_JWT_DE_EXEMPLO, Settings
from app.core.database import SessionLocal
from app.main import app
from app.models.match import Match, MatchAnswer
from app.models.question import Question, QuestionStatus


def novo_nome() -> str:
    return f"user_{uuid.uuid4().hex[:8]}"


def iniciar(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post("/matches", json={}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def paralelo(acao, vezes: int = 8) -> list:
    """Roda `acao(cliente)` em `vezes` threads soltas ao mesmo tempo."""
    barreira = threading.Barrier(vezes)
    resultados: list = []

    def rodar() -> None:
        cliente = TestClient(app)
        barreira.wait()
        resultados.append(acao(cliente))

    threads = [threading.Thread(target=rodar) for _ in range(vezes)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return resultados


def test_respostas_simultaneas_contam_uma_vez(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    match_id = iniciar(client, auth_headers)
    question = client.get(f"/matches/{match_id}/next-question", headers=auth_headers).json()
    payload = {"question_id": question["id"], "reliability": 50}
    url = f"/matches/{match_id}/answers"

    codigos = paralelo(lambda c: c.post(url, json=payload, headers=auth_headers).status_code)

    assert sorted(codigos) == [200] + [422] * 7
    with SessionLocal() as db:
        respostas = db.scalars(select(MatchAnswer).where(MatchAnswer.match_id == match_id)).all()
    assert len(respostas) == 1


def test_encerramentos_simultaneos_contam_uma_vez(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    match_id = iniciar(client, auth_headers)
    url = f"/matches/{match_id}/finish"

    codigos = paralelo(lambda c: c.post(url, headers=auth_headers).status_code)

    assert sorted(codigos) == [200] + [409] * 7
    assert client.get("/progress/me", headers=auth_headers).json()["matches_played"] == 1


def test_encerrar_partidas_ao_mesmo_tempo_soma_todos_os_pontos(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # Pela API só fica uma partida aberta; as outras três entram direto no banco (o caso de
    # partidas abertas antes desta regra).
    primeira = iniciar(client, auth_headers)
    with SessionLocal() as db:
        modelo = db.get(Match, primeira)
        modelo.score = 10
        partidas = [primeira]
        for _ in range(3):
            outra = Match(
                user_id=modelo.user_id,
                level_id=modelo.level_id,
                duration_seconds=modelo.duration_seconds,
                score=10,
            )
            db.add(outra)
            db.flush()
            partidas.append(outra.id)
        db.commit()
    fila = iter(partidas)
    trava = threading.Lock()

    def encerrar(c: TestClient) -> int:
        with trava:
            match_id = next(fila)
        return c.post(f"/matches/{match_id}/finish", headers=auth_headers).status_code

    assert paralelo(encerrar, vezes=4) == [200] * 4
    progresso = client.get("/progress/me", headers=auth_headers).json()
    assert progresso["matches_played"] == 4
    assert progresso["total_score"] == 40


def test_partida_nova_abandona_a_aberta(client: TestClient, auth_headers: dict[str, str]) -> None:
    primeira = iniciar(client, auth_headers)
    iniciar(client, auth_headers)

    assert client.get(f"/matches/{primeira}", headers=auth_headers).json()["status"] == "abandoned"
    assert client.post(f"/matches/{primeira}/finish", headers=auth_headers).status_code == 409
    assert client.get("/progress/me", headers=auth_headers).json()["matches_played"] == 0


def test_resposta_fora_do_tempo_vale_como_erro(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    match_id = iniciar(client, auth_headers)
    question = client.get(f"/matches/{match_id}/next-question", headers=auth_headers).json()
    with SessionLocal() as db:
        db.get(Match, match_id).current_question_served_at = datetime.now(timezone.utc) - timedelta(
            minutes=10
        )
        referencia = db.get(Question, question["id"]).reliability_reference
        db.commit()

    body = client.post(
        f"/matches/{match_id}/answers",
        json={"question_id": question["id"], "reliability": referencia},
        headers=auth_headers,
    ).json()

    assert body["timed_out"] is True
    assert body["is_correct"] is False
    assert body["score"] == 0


def test_resposta_no_tempo_nao_e_marcada(client: TestClient, auth_headers: dict[str, str]) -> None:
    match_id = iniciar(client, auth_headers)
    question = client.get(f"/matches/{match_id}/next-question", headers=auth_headers).json()

    body = client.post(
        f"/matches/{match_id}/answers",
        json={"question_id": question["id"], "reliability": 50},
        headers=auth_headers,
    ).json()

    assert body["timed_out"] is False


def test_pergunta_despublicada_e_trocada(client: TestClient, auth_headers: dict[str, str]) -> None:
    match_id = iniciar(client, auth_headers)
    with SessionLocal() as db:
        category_id = db.scalars(select(Question.category_id)).first()
        rejeitada = Question(
            statement=f"Afirmação rejeitada {uuid.uuid4().hex}",
            is_true=True,
            reliability_reference=90,
            explanation="Explicação de teste.",
            source=f"teste-{uuid.uuid4().hex}",
            category_id=category_id,
            status=QuestionStatus.REJECTED,
        )
        db.add(rejeitada)
        db.flush()
        db.get(Match, match_id).current_question_id = rejeitada.id
        db.commit()
        rejeitada_id = rejeitada.id

    question = client.get(f"/matches/{match_id}/next-question", headers=auth_headers).json()

    assert question["id"] != rejeitada_id


def test_nivel_zero_e_invalido(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.post("/matches", json={"level": 0}, headers=auth_headers).status_code == 422


def test_cadastro_exige_oito_caracteres(client: TestClient) -> None:
    response = client.post("/auth/register", json={"username": novo_nome(), "password": "1234567"})

    assert response.status_code == 422


def test_senha_acima_de_72_bytes_e_recusada(client: TestClient) -> None:
    # 40 caracteres, 80 bytes em UTF-8.
    response = client.post("/auth/register", json={"username": novo_nome(), "password": "ç" * 40})

    assert response.status_code == 422


def test_login_bloqueia_depois_de_falhas_seguidas(client: TestClient) -> None:
    username = novo_nome()
    client.post("/auth/register", json={"username": username, "password": "segredo1"})
    errada = {"username": username, "password": "errada"}

    codigos = [client.post("/auth/login", json=errada).status_code for _ in range(6)]
    certa = client.post("/auth/login", json={"username": username, "password": "segredo1"})

    assert codigos == [401] * 5 + [429]
    assert certa.status_code == 429


def test_cadastros_simultaneos_com_o_mesmo_nome(client: TestClient) -> None:
    credenciais = {"username": novo_nome(), "password": "segredo1"}

    codigos = paralelo(lambda c: c.post("/auth/register", json=credenciais).status_code, vezes=6)

    assert sorted(codigos) == [201] + [409] * 5


def test_token_assinado_com_o_segredo_de_exemplo_e_recusado(client: TestClient) -> None:
    forjado = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        SEGREDO_JWT_DE_EXEMPLO,
        algorithm="HS256",
    )

    response = client.get("/users/me", headers={"Authorization": f"Bearer {forjado}"})

    assert response.status_code == 401


@pytest.mark.parametrize("segredo", ["", "curto", SEGREDO_JWT_DE_EXEMPLO])
def test_segredo_jwt_fraco_e_recusado(segredo: str) -> None:
    with pytest.raises(RuntimeError):
        Settings(jwt_secret=segredo).exigir_segredo_jwt()


def test_segredo_jwt_de_32_bytes_e_aceito() -> None:
    assert Settings(jwt_secret="x" * 32).exigir_segredo_jwt() == "x" * 32
