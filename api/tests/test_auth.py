import uuid

from fastapi.testclient import TestClient


def new_username() -> str:
    return f"user_{uuid.uuid4().hex[:8]}"


def test_register_and_login(client: TestClient) -> None:
    credentials = {"username": new_username(), "password": "segredo1"}

    assert client.post("/auth/register", json=credentials).status_code == 201
    response = client.post("/auth/login", json=credentials)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_register_duplicated_username(client: TestClient) -> None:
    credentials = {"username": new_username(), "password": "segredo1"}
    client.post("/auth/register", json=credentials)

    assert client.post("/auth/register", json=credentials).status_code == 409


def test_login_with_wrong_password(client: TestClient) -> None:
    username = new_username()
    client.post("/auth/register", json={"username": username, "password": "segredo1"})

    response = client.post("/auth/login", json={"username": username, "password": "errada"})

    assert response.status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/users/me").status_code == 401


def test_me(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/users/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["is_admin"] is False
