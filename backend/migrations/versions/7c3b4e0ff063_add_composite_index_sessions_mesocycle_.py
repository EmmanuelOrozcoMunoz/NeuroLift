"""add composite index sessions mesocycle date and sets exercise index

Revision ID: 7c3b4e0ff063
Revises: bc48a974c56c
Create Date: 2026-09-21 22:09:08.159902

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c3b4e0ff063'
down_revision: Union[str, Sequence[str], None] = 'bc48a974c56c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Los endpoints bulk-* de grupo (groups.py) y el leaderboard de WOD filtran exactamente por
    # (mesocycle_id, scheduled_date) -- sin este índice compuesto, el índice simple de
    # mesocycle_id ya existente resuelve el filtro por mesociclo pero sigue escaneando fila por
    # fila para el filtro de fecha.
    op.create_index(
        "ix_sessions_mesocycle_scheduled_date",
        "sessions",
        ["mesocycle_id", "scheduled_date"],
    )
    # `sets` será la tabla más grande del sistema (una fila por serie, por sesión, por atleta);
    # exercise_id no tenía índice pese a ser FK -- barato agregarlo ahora, caro reindexar después
    # con la tabla ya grande.
    op.create_index("ix_sets_exercise_id", "sets", ["exercise_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_sets_exercise_id", table_name="sets")
    op.drop_index("ix_sessions_mesocycle_scheduled_date", table_name="sessions")
