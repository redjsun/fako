"""origem da alegacao e afirmacao classificada nas questoes

Revision ID: 7d2e4f6a8b10
Revises: 3e9b7c1d5f20
Create Date: 2026-10-14 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7d2e4f6a8b10'
down_revision: Union[str, None] = '3e9b7c1d5f20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('claim_text', sa.Text(), nullable=True))
    op.add_column('questions', sa.Column('origin_author', sa.String(length=200), nullable=True))
    op.add_column('questions', sa.Column('origin_link', sa.String(length=500), nullable=True))
    op.add_column('questions', sa.Column('origin_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('questions', 'origin_date')
    op.drop_column('questions', 'origin_link')
    op.drop_column('questions', 'origin_author')
    op.drop_column('questions', 'claim_text')
