"""regras de dificuldade por nível

Revision ID: 7d2a4c9e1b63
Revises: 3e9b7c1d5f20
Create Date: 2026-10-15 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7d2a4c9e1b63'
down_revision: Union[str, None] = '3e9b7c1d5f20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mesma tabela de app/seeds/data.py. O seed só insere níveis que faltam, então os bancos
# já populados recebem as regras novas por aqui.
COLUNAS = (
    'board_size',
    'tick_ms',
    'min_score_to_advance',
    'match_seconds',
    'question_seconds',
    'reliability_tolerance',
    'wrong_answer_penalty',
    'growth_per_error',
    'solid_walls',
    'apple_lifetime_seconds',
    'rotten_apples',
)
NIVEIS = {
    1: (16, 160, 30, 120, 45, 15, 0, 1, False, None, 0),
    2: (16, 145, 40, 120, 40, 15, 0, 1, False, None, 0),
    3: (14, 130, 50, 110, 35, 12, 0, 2, False, None, 0),
    4: (14, 125, 50, 100, 30, 10, 5, 2, True, 12, 0),
    5: (12, 115, 60, 90, 25, 10, 5, 2, True, 10, 2),
    6: (12, 105, 70, 90, 20, 8, 10, 3, True, 8, 4),
}
# Valores anteriores, para o downgrade.
NIVEIS_ANTERIORES = {
    1: (7, 400),
    2: (7, 350),
    3: (7, 300),
    4: (6, 300),
    5: (6, 250),
    6: (6, 200),
}


def upgrade() -> None:
    # Os padrões são as regras do nível 1, que eram as regras de todas as partidas.
    op.add_column('levels', sa.Column('match_seconds', sa.Integer(), server_default='120', nullable=False))
    op.add_column('levels', sa.Column('question_seconds', sa.Integer(), server_default='45', nullable=False))
    op.add_column('levels', sa.Column('reliability_tolerance', sa.Integer(), server_default='15', nullable=False))
    op.add_column('levels', sa.Column('wrong_answer_penalty', sa.Integer(), server_default='0', nullable=False))
    op.add_column('levels', sa.Column('growth_per_error', sa.Integer(), server_default='1', nullable=False))
    op.add_column('levels', sa.Column('solid_walls', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('levels', sa.Column('apple_lifetime_seconds', sa.Integer(), nullable=True))
    op.add_column('levels', sa.Column('rotten_apples', sa.Integer(), server_default='0', nullable=False))

    levels = sa.table('levels', sa.column('number', sa.Integer()), *(sa.column(nome) for nome in COLUNAS))
    for numero, valores in NIVEIS.items():
        op.execute(
            levels.update()
            .where(levels.c.number == numero)
            .values(dict(zip(COLUNAS, valores, strict=True)))
        )


def downgrade() -> None:
    levels = sa.table(
        'levels',
        sa.column('number', sa.Integer()),
        sa.column('board_size', sa.Integer()),
        sa.column('tick_ms', sa.Integer()),
    )
    for numero, (board_size, tick_ms) in NIVEIS_ANTERIORES.items():
        op.execute(
            levels.update()
            .where(levels.c.number == numero)
            .values(board_size=board_size, tick_ms=tick_ms)
        )
    for coluna in reversed(COLUNAS[3:]):
        op.drop_column('levels', coluna)
