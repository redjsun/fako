"""resposta única por questão e hora em que a pergunta foi servida

Revision ID: 9f4b2d6a1c38
Revises: 7d2a4c9e1b63
Create Date: 2026-10-16 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9f4b2d6a1c38'
down_revision: Union[str, None] = '7d2a4c9e1b63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'matches',
        sa.Column('current_question_served_at', sa.DateTime(timezone=True), nullable=True),
    )
    # Respostas repetidas (pedidos simultâneos antes do lock da partida): fica a primeira.
    op.execute(
        """
        DELETE FROM match_answers
        WHERE id NOT IN (
            SELECT MIN(id) FROM match_answers GROUP BY match_id, question_id
        )
        """
    )
    op.create_unique_constraint(
        'uq_match_answers_match_question', 'match_answers', ['match_id', 'question_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_match_answers_match_question', 'match_answers', type_='unique')
    op.drop_column('matches', 'current_question_served_at')
