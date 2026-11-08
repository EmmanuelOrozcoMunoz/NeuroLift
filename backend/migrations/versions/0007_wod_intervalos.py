"""WOD por intervalos: Session.wod_intervals y Session.wod_interval_times.

El coach fija cuántos intervalos tiene el WOD y el atleta anota el tiempo de cada uno; el total (en
wod_time_seconds) ordena el leaderboard, gana el menor. Columnas aditivas y nullable: todo lo que ya existe
sigue igual.

Revision ID: 0007
Revises: 0006
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("wod_intervals", sa.Integer(), nullable=True))
    op.add_column("sessions", sa.Column("wod_interval_times", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "wod_interval_times")
    op.drop_column("sessions", "wod_intervals")
