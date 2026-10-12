"""DTOs (Data Transfer Objects) para o serviço de inferência do BERTimbau."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    """Payload de entrada para análise de uma afirmação."""

    statement: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Texto ou afirmação a ser analisada pelos classificadores.",
        examples=["Vacina da gripe altera o DNA humano segundo vídeo compartilhado em redes."],
    )

    @field_validator("statement")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        trimmed = v.strip()
        if len(trimmed) < 5:
            raise ValueError(
                "A afirmação deve conter no mínimo 5 caracteres significativos (não apenas espaços)."
            )
        return trimmed


class ModelTargetResult(BaseModel):
    """Resultado individual de um dos classificadores (Y1 ou Y2)."""

    target: str
    target_description: str
    predicted_class: int
    predicted_label: str
    softmax_scores: dict[str, float]


class EducationalAssessment(BaseModel):
    """Interpretação pedagógica preliminar da combinação Y1 e Y2."""

    status: str
    label: str
    summary: str
    is_inconclusive: bool


class ModelMetadataResponse(BaseModel):
    """Informações e rastreabilidade dos pesos e artefatos em uso."""

    model_name: str
    version: str
    device: str
    training_timestamp: str | None = None
    dataset_hash: str | None = None


class AnalyzeResponse(BaseModel):
    """Contrato de resposta da inferência."""

    statement: str
    cleaned_statement: str
    educational_assessment: EducationalAssessment
    y1: ModelTargetResult
    y2: ModelTargetResult
    model_info: ModelMetadataResponse
    disclaimer: str
    methodology_note: str
