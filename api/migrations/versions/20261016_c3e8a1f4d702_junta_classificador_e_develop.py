"""junta as migrations do classificador (explicacao e detalhe da fonte) com as da develop

Revision ID: c3e8a1f4d702
Revises: b6d1f3a8c925, 9f4b2d6a1c38
Create Date: 2026-10-16 02:30:00.000000
"""
from typing import Sequence, Union


revision: str = 'c3e8a1f4d702'
down_revision: Union[str, Sequence[str], None] = ('b6d1f3a8c925', '9f4b2d6a1c38')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
