"""Popula o banco com os dados iniciais. Idempotente: pode rodar mais de uma vez.

Uso: python -m app.seeds.run
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Category, Level, Question, QuestionOrigin, QuestionStatus
from app.seeds.data import CATEGORIES, LEVELS, QUESTIONS


def seed_categories(db: Session) -> dict[str, Category]:
    categories = {c.slug: c for c in db.scalars(select(Category))}
    for data in CATEGORIES:
        if data["slug"] not in categories:
            category = Category(**data)
            db.add(category)
            categories[data["slug"]] = category
    db.flush()
    return categories


def seed_levels(db: Session) -> None:
    existing = set(db.scalars(select(Level.number)))
    db.add_all(Level(**data) for data in LEVELS if data["number"] not in existing)


def seed_questions(db: Session, categories: dict[str, Category]) -> None:
    existing = set(db.scalars(select(Question.statement)))
    now = datetime.now(timezone.utc)
    for data in QUESTIONS:
        if data["statement"] in existing:
            continue
        db.add(
            Question(
                statement=data["statement"],
                is_true=data["is_true"],
                reliability_reference=data["reliability_reference"],
                explanation=data["explanation"],
                source=data["source"],
                category_id=categories[data["category"]].id,
                status=QuestionStatus.VALIDATED,
                origin=QuestionOrigin.HUMAN,
                validated_at=now,
            )
        )


def main() -> None:
    with SessionLocal.begin() as db:
        categories = seed_categories(db)
        seed_levels(db)
        seed_questions(db, categories)
    print("Seed concluído.")


if __name__ == "__main__":
    main()
