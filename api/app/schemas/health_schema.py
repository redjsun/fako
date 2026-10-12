"""DTOs de entrada e saída da API."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
