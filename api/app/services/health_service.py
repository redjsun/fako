"""Camada de negócio: regras da aplicação, sem conhecer HTTP."""

from app.schemas.health_schema import HealthResponse


class HealthService:
    def check(self) -> HealthResponse:
        return HealthResponse(status="ok")
