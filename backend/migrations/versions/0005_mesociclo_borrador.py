"""Borrador: un mesociclo armado por la IA queda oculto al atleta hasta que el coach lo publique.

Columna aditiva con valor por defecto falso: todo lo que ya existe sigue publicado, y el código
anterior ignora la columna nueva (se puede migrar antes de desplegar).

Revision ID: 0005
Revises: 0004
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mesocycles",
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("mesocycles", "is_draft")
