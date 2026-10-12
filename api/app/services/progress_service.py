"""Consulta e atualização do progresso do jogador."""

from sqlalchemy.orm import Session

from app.models.progress import UserProgress
from app.models.user import User
from app.repositories.progress_repository import ProgressRepository
from app.schemas.progress_schema import ProgressResponse


class ProgressService:
    def __init__(self, db: Session) -> None:
        self.progress = ProgressRepository(db)

    def get_or_create(self, user_id: int) -> UserProgress:
        progress = self.progress.get_by_user(user_id)
        if progress is None:
            progress = self.progress.add(UserProgress(user_id=user_id))
        return progress

    def get(self, user: User) -> ProgressResponse:
        return ProgressResponse.model_validate(self.get_or_create(user.id))
