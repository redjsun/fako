"""DTOs de níveis."""

from pydantic import BaseModel, ConfigDict


class LevelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: int
    board_size: int
    tick_ms: int
    min_score_to_advance: int
