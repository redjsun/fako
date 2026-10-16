"""Rotas de níveis."""

from fastapi import APIRouter, Depends

from app.core.database import SessaoDaRequisicao
from app.schemas.level_schema import LevelResponse
from app.services.level_service import LevelService

router = APIRouter(prefix="/levels", tags=["levels"])


def get_service(db: SessaoDaRequisicao) -> LevelService:
    return LevelService(db)


@router.get("", response_model=list[LevelResponse])
def list_levels(service: LevelService = Depends(get_service)) -> list[LevelResponse]:
    return service.list()
