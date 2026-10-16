import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.progress import UserProgress
from app.models.user import User
from app.seeds.data import LEVELS
from app.services import game_rules


def start_match(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post("/matches", json={}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def test_new_player_starts_at_level_one(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/matches", json={}, headers=auth_headers)

    assert response.json()["level"] == LEVELS[0]
    assert response.json()["duration_seconds"] == LEVELS[0]["match_seconds"]


def test_locked_level(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/matches", json={"level": 4}, headers=auth_headers)

    assert response.status_code == 422


def test_question_does_not_expose_answer(client: TestClient, auth_headers: dict[str, str]) -> None:
    match_id = start_match(client, auth_headers)

    question = client.get(f"/matches/{match_id}/next-question", headers=auth_headers).json()

    assert set(question) == {"id", "statement", "category"}


def test_answer_returns_feedback(client: TestClient, auth_headers: dict[str, str]) -> None:
    match_id = start_match(client, auth_headers)
    question = client.get(f"/matches/{match_id}/next-question", headers=auth_headers).json()

    response = client.post(
        f"/matches/{match_id}/answers",
        json={"question_id": question["id"], "reliability": 70},
        headers=auth_headers,
    )

    body = response.json()
    assert response.status_code == 200
    assert body["reliability"] == 70
    assert body["tolerance"] == 15
    assert body["distance"] == abs(70 - body["reliability_reference"])
    assert body["is_correct"] == (body["distance"] <= 15)
    assert body["explanation"]
    assert body["score"] == (10 if body["is_correct"] else 0)


def test_tolerance_boundaries() -> None:
    assert game_rules.is_within_tolerance(40, 40, 15)
    assert game_rules.is_within_tolerance(55, 40, 15)
    assert not game_rules.is_within_tolerance(56, 40, 15)
    assert not game_rules.is_within_tolerance(24, 40, 15)
    assert game_rules.is_within_tolerance(48, 40, 8)
    assert not game_rules.is_within_tolerance(49, 40, 8)


def test_wrong_answer_penalty_never_makes_score_negative() -> None:
    assert game_rules.score_after_answer(20, True, 10) == 30
    assert game_rules.score_after_answer(20, False, 10) == 10
    assert game_rules.score_after_answer(5, False, 10) == 0
    assert game_rules.score_after_answer(5, False, 0) == 5


def test_levels_list_every_rule(client: TestClient) -> None:
    response = client.get("/levels")

    assert response.json() == LEVELS


def unlock_levels(client: TestClient, highest_level: int) -> dict[str, str]:
    """Jogador novo com os níveis liberados até `highest_level`."""
    username = f"jogador_{uuid.uuid4().hex[:8]}"
    token = client.post(
        "/auth/register", json={"username": username, "password": "segredo1"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    start_match(client, headers)  # cria o progresso do jogador
    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.username == username))
        progress = db.scalar(select(UserProgress).where(UserProgress.user_id == user_id))
        progress.current_level = highest_level
        progress.highest_level = highest_level
        db.commit()
    return headers


def test_last_level_uses_its_own_rules(client: TestClient) -> None:
    headers = unlock_levels(client, 6)
    last_level = LEVELS[5]

    match = client.post("/matches", json={"level": 6}, headers=headers).json()
    question = client.get(f"/matches/{match['id']}/next-question", headers=headers).json()
    body = client.post(
        f"/matches/{match['id']}/answers",
        json={"question_id": question["id"], "reliability": 50},
        headers=headers,
    ).json()

    assert match["duration_seconds"] == last_level["match_seconds"]
    assert body["tolerance"] == last_level["reliability_tolerance"]
    assert body["is_correct"] == (body["distance"] <= last_level["reliability_tolerance"])
    # Começa em 0: o erro não deixa o placar negativo.
    assert body["score"] == (10 if body["is_correct"] else 0)


def test_only_the_served_question_can_be_answered(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    other_match = start_match(client, auth_headers)
    question = client.get(f"/matches/{other_match}/next-question", headers=auth_headers).json()
    match_id = start_match(client, auth_headers)

    response = client.post(
        f"/matches/{match_id}/answers",
        json={"question_id": question["id"], "reliability": 50},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_pending_question_is_served_again(client: TestClient, auth_headers: dict[str, str]) -> None:
    match_id = start_match(client, auth_headers)
    url = f"/matches/{match_id}/next-question"

    first = client.get(url, headers=auth_headers).json()
    second = client.get(url, headers=auth_headers).json()

    assert first == second


def test_answer_limit_per_match(
    client: TestClient, auth_headers: dict[str, str], monkeypatch
) -> None:
    monkeypatch.setattr(game_rules, "MAX_ANSWERS_PER_MATCH", 1)
    match_id = start_match(client, auth_headers)
    url = f"/matches/{match_id}/next-question"
    question = client.get(url, headers=auth_headers).json()
    client.post(
        f"/matches/{match_id}/answers",
        json={"question_id": question["id"], "reliability": 50},
        headers=auth_headers,
    )

    assert client.get(url, headers=auth_headers).status_code == 422


def test_reliability_out_of_range(client: TestClient, auth_headers: dict[str, str]) -> None:
    match_id = start_match(client, auth_headers)
    question = client.get(f"/matches/{match_id}/next-question", headers=auth_headers).json()

    response = client.post(
        f"/matches/{match_id}/answers",
        json={"question_id": question["id"], "reliability": 120},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_same_question_cannot_be_answered_twice(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    match_id = start_match(client, auth_headers)
    question = client.get(f"/matches/{match_id}/next-question", headers=auth_headers).json()
    payload = {"question_id": question["id"], "reliability": 50}

    client.post(f"/matches/{match_id}/answers", json=payload, headers=auth_headers)
    response = client.post(f"/matches/{match_id}/answers", json=payload, headers=auth_headers)

    assert response.status_code == 422


def test_finish_updates_progress(client: TestClient, auth_headers: dict[str, str]) -> None:
    match_id = start_match(client, auth_headers)

    result = client.post(f"/matches/{match_id}/finish", headers=auth_headers).json()
    progress = client.get("/progress/me", headers=auth_headers).json()

    assert result["match"]["status"] == "finished"
    assert result["advanced"] is False
    assert progress["matches_played"] == 1
    assert progress["current_level"] == 1


def test_admin_routes_are_restricted(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get("/admin/questions", headers=auth_headers).status_code == 403
