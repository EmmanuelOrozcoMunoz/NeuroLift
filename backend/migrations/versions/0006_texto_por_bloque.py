"""Texto libre por bloque: Session.block_notes.

El coach puede programar cada bloque de un día (fuerza, weightlifting, skills, accesorios, principal)
como un bloc de notas. Columna aditiva y nullable: todo lo que ya existe sigue igual, y el código
anterior (que no la conoce) la ignora.

Revision ID: 0006
Revises: 0005
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("block_notes", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "block_notes")
