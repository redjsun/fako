"""Conexão com o banco de dados (camada de infraestrutura)."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Abre uma sessão por requisição: commit ao final, rollback em caso de erro."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Sessão das rotas. Com o escopo "function", o commit roda quando a rota termina e antes de a
# resposta sair: uma falha no commit vira erro para o cliente, e a próxima chamada já enxerga os
# dados. Com o escopo padrão ("request"), o FastAPI só fecha a dependência depois de enviar a
# resposta. Use sempre este tipo: o cache de dependências separa por escopo, então misturar com
# `Depends(get_db)` abriria duas sessões na mesma requisição.
SessaoDaRequisicao = Annotated[Session, Depends(get_db, scope="function")]
