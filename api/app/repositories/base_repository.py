"""Camada de acesso a dados: isola as fontes de dados do restante do sistema."""

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import Entity

T = TypeVar("T", bound=Entity)


class BaseRepository(Generic[T]):
    """CRUD genérico; repositórios concretos definem `model` e consultas próprias."""

    model: type[T]

    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[T]:
        return list(self.db.scalars(select(self.model).order_by(self.model.id)))

    def get(self, entity_id: int) -> T | None:
        return self.db.get(self.model, entity_id)

    def add(self, entity: T) -> T:
        self.db.add(entity)
        self.db.flush()
        return entity

    def delete(self, entity: T) -> None:
        self.db.delete(entity)
        self.db.flush()
