"""Fixtures dos testes: banco migrado e populado, cliente HTTP e usuário autenticado.

Os testes usam o banco apontado por DATABASE_URL; use um banco separado do de
desenvolvimento (ex.: fako_test), como fazem o `make test` e o CI.
"""

import os

# Antes de importar a aplicação, que não sobe sem um JWT_SECRET válido.
os.environ.setdefault("JWT_SECRET", "segredo-dos-testes-nao-usar-em-producao-0123456789")

import uuid  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from app.core.database import engine  # noqa: E402
from app.core.rate_limit import limite_de_login  # noqa: E402
from app.main import app  # noqa: E402
from app.seeds.run import main as seed  # noqa: E402

banco_disponivel = False


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    # Sem PostgreSQL ainda rodam os testes unitários (ex.: inferência) e os de banco são
    # pulados; com ele, uma falha de migração ou de seed derruba a suíte em vez de aparecer
    # como erro em outro teste.
    global banco_disponivel
    try:
        with engine.connect():
            pass
    except OperationalError:
        return
    command.upgrade(Config("alembic.ini"), "head")
    seed()
    banco_disponivel = True


@pytest.fixture(autouse=True)
def sem_limite_de_login() -> None:
    # Todos os testes vêm da mesma origem ("testclient"): as falhas de um não contam no outro.
    limite_de_login.limpar()


@pytest.fixture
def client() -> TestClient:
    if not banco_disponivel:
        pytest.skip("PostgreSQL indisponível (DATABASE_URL)")
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    username = f"jogador_{uuid.uuid4().hex[:8]}"
    response = client.post("/auth/register", json={"username": username, "password": "segredo1"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
