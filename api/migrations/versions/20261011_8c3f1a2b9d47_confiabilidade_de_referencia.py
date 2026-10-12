"""confiabilidade de referência

Revision ID: 8c3f1a2b9d47
Revises: 5b1e7c9d2a40
Create Date: 2026-10-11 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8c3f1a2b9d47'
down_revision: Union[str, None] = '5b1e7c9d2a40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('reliability_reference', sa.Integer(), nullable=True))
    # Questões já cadastradas recebem a referência derivada de is_true.
    op.execute(
        "UPDATE questions SET reliability_reference = CASE WHEN is_true THEN 90 ELSE 10 END"
    )
    op.alter_column('questions', 'reliability_reference', nullable=False)
    op.add_column('match_answers', sa.Column('reliability', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('match_answers', 'reliability')
    op.drop_column('questions', 'reliability_reference')
