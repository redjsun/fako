"""Importa todas as entidades para registrá-las no metadata (usado pelo Alembic)."""

from app.models.base import Base, Entity
from app.models.category import Category
from app.models.level import Level
from app.models.match import Match, MatchAnswer, MatchStatus
from app.models.progress import UserProgress
from app.models.question import Question, QuestionOrigin, QuestionStatus
from app.models.user import User

__all__ = [
    "Base",
    "Category",
    "Entity",
    "Level",
    "Match",
    "MatchAnswer",
    "MatchStatus",
    "Question",
    "QuestionOrigin",
    "QuestionStatus",
    "User",
    "UserProgress",
]
