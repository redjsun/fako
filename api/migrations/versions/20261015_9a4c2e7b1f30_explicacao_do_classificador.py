"""explicacao didatica do classificador nas questoes

Revision ID: 9a4c2e7b1f30
Revises: 7d2e4f6a8b10
Create Date: 2026-10-15 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9a4c2e7b1f30'
down_revision: Union[str, None] = '7d2e4f6a8b10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('model_explanation', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('questions', 'model_explanation')
