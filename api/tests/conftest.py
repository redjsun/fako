"""Fixtures dos testes: banco migrado e populado, cliente HTTP e usuário autenticado.

Os testes usam o banco apontado por DATABASE_URL; use um banco separado do de
desenvolvimento (ex.: fako_test), como fazem o `make test` e o CI.
"""

import uuid

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.database import engine
from app.integrations.classificador_client import FakeClassificador, get_classificador
from app.integrations.llm_client import FakeLLMClient, get_llm_client
from app.main import app
from app.seeds.run import main as seed


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    # Sem PostgreSQL ainda rodam os testes unitários (ex.: inferência); com ele, uma falha de
    # migração ou de seed derruba a suíte em vez de aparecer como erro em outro teste.
    try:
        with engine.connect():
            pass
    except OperationalError:
        return
    command.upgrade(Config("alembic.ini"), "head")
    seed()


@pytest.fixture(autouse=True)
def clientes_fake():
    """LLM e classificador fake em todos os testes, seja qual for o .env; cada teste pode
    sobrescrever. Os overrides são limpos no fim de cada teste."""
    app.dependency_overrides[get_llm_client] = FakeLLMClient
    app.dependency_overrides[get_classificador] = FakeClassificador
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    username = f"jogador_{uuid.uuid4().hex[:8]}"
    response = client.post("/auth/register", json={"username": username, "password": "segredo1"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
