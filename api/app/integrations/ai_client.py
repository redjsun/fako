"""Cliente de IA: interface única para o provedor escolhido pelo grupo.

A IA atua nos bastidores, gerando e classificando conteúdo. Tudo que ela produz
entra como rascunho e depende de validação humana.
"""

from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings


@dataclass
class GeneratedQuestion:
    statement: str
    is_true: bool
    explanation: str
    source: str


@dataclass
class Classification:
    suggested_is_true: bool
    confidence: float
    rationale: str


class AIClient(Protocol):
    def generate_questions(self, category: str, quantity: int) -> list[GeneratedQuestion]: ...

    def classify(self, statement: str) -> Classification: ...


class FakeAIClient:
    """Implementação local, sem chamadas externas, para desenvolvimento e testes."""

    def generate_questions(self, category: str, quantity: int) -> list[GeneratedQuestion]:
        return [
            GeneratedQuestion(
                statement=f"[rascunho IA] Afirmação {i + 1} sobre {category}.",
                is_true=i % 2 == 0,
                explanation="Explicação gerada automaticamente — revisar antes de publicar.",
                source="A definir na validação",
            )
            for i in range(quantity)
        ]

    def classify(self, statement: str) -> Classification:
        return Classification(
            suggested_is_true=False,
            confidence=0.0,
            rationale="Classificador fake: configure um provedor real em AI_PROVIDER.",
        )


def get_ai_client() -> AIClient:
    provider = get_settings().ai_provider
    if provider == "fake":
        return FakeAIClient()
    # TODO: adicionar o provedor real escolhido pelo grupo (ex.: Anthropic, OpenAI).
    raise ValueError(f"Provedor de IA não suportado: {provider}")
