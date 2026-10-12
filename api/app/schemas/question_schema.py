"""DTOs de questões exibidas ao jogador.

A resposta correta e a explicação não vão para o front antes da resposta do jogador.
"""

from pydantic import BaseModel


class QuestionResponse(BaseModel):
    id: int
    statement: str
    category: str
