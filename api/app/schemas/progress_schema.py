"""DTOs de progresso da jornada."""

from pydantic import BaseModel, ConfigDict


class ProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_level: int
    highest_level: int
    total_score: int
    matches_played: int
