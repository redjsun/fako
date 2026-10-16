"""detalhe da fonte nas questoes (titulo da checagem ou resumo da materia)

Revision ID: b6d1f3a8c925
Revises: 9a4c2e7b1f30
Create Date: 2026-10-15 23:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b6d1f3a8c925'
down_revision: Union[str, None] = '9a4c2e7b1f30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('source_detail', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('questions', 'source_detail')
