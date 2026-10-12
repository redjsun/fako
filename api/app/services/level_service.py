"""Consulta dos níveis de dificuldade."""

from sqlalchemy.orm import Session

from app.repositories.level_repository import LevelRepository
from app.schemas.level_schema import LevelResponse


class LevelService:
    def __init__(self, db: Session) -> None:
        self.levels = LevelRepository(db)

    def list(self) -> list[LevelResponse]:
        return [LevelResponse.model_validate(level) for level in self.levels.list()]
