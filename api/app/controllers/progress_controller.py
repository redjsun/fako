"""Rotas de progresso da jornada."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.progress_schema import ProgressResponse
from app.services.progress_service import ProgressService

router = APIRouter(prefix="/progress", tags=["progress"])


def get_service(db: Session = Depends(get_db)) -> ProgressService:
    return ProgressService(db)


@router.get("/me", response_model=ProgressResponse)
def my_progress(
    user: User = Depends(get_current_user),
    service: ProgressService = Depends(get_service),
) -> ProgressResponse:
    return service.get(user)
