"""pergunta atual da partida

Revision ID: 3e9b7c1d5f20
Revises: 8c3f1a2b9d47
Create Date: 2026-10-12 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3e9b7c1d5f20'
down_revision: Union[str, None] = '8c3f1a2b9d47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('matches', sa.Column('current_question_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_matches_current_question_id_questions',
        'matches',
        'questions',
        ['current_question_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_matches_current_question_id_questions', 'matches', type_='foreignkey')
    op.drop_column('matches', 'current_question_id')
