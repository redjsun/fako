"""Camada de apresentação: expõe as rotas e delega para os serviços."""

from fastapi import APIRouter, Depends

from app.schemas.health_schema import HealthResponse
from app.services.health_service import HealthService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(service: HealthService = Depends(HealthService)) -> HealthResponse:
    return service.check()
