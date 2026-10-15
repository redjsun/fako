"""DTOs de níveis."""

from pydantic import BaseModel, ConfigDict


class LevelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: int
    board_size: int
    tick_ms: int
    min_score_to_advance: int
    match_seconds: int
    question_seconds: int
    reliability_tolerance: int
    wrong_answer_penalty: int
    growth_per_error: int
    solid_walls: bool
    apple_lifetime_seconds: int | None
    rotten_apples: int
