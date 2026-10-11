"""analise do classificador nas questoes

Revision ID: 5b1e7c9d2a40
Revises: 067bd9f46759
Create Date: 2026-10-11 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5b1e7c9d2a40'
down_revision: Union[str, None] = '067bd9f46759'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('model_category', sa.String(length=20), nullable=True))
    op.add_column('questions', sa.Column('model_score', sa.Float(), nullable=True))
    op.add_column('questions', sa.Column('model_confidence', sa.Float(), nullable=True))
    op.add_column('questions', sa.Column('model_version', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('questions', 'model_version')
    op.drop_column('questions', 'model_confidence')
    op.drop_column('questions', 'model_score')
    op.drop_column('questions', 'model_category')
