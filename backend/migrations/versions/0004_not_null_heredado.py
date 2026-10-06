"""Exige NOT NULL en las columnas que los modelos ya declaran obligatorias.

Dev ya las tenía así; QA (creada con modelos más viejos vía `create_all`) las permitía nulas.
Es no-op donde ya son NOT NULL (bases nuevas y Dev). Si una fila trae NULL en alguna, el
ALTER falla y la migración se revierte entera (DDL transaccional): hay que corregir ese dato
a mano antes de reintentar. Solo `users.role` se rellena sola ("athlete", el valor por defecto).

Revision ID: 0004
Revises: 0003
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OBLIGATORIAS = (
    ("users", "full_name"),
    ("users", "email"),
    ("users", "role"),
    ("personal_records", "exercise_name"),
    ("personal_records", "max_weight_kg"),
)


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'athlete'")
    for tabla, columna in _OBLIGATORIAS:
        col = next(c for c in insp.get_columns(tabla) if c["name"] == columna)
        if not col["nullable"]:
            continue
        if (tabla, columna) == ("users", "role"):
            op.execute("UPDATE users SET role = 'athlete' WHERE role IS NULL")
        op.execute(f'ALTER TABLE {tabla} ALTER COLUMN "{columna}" SET NOT NULL')


def downgrade() -> None:
    # Solo acerca la base al estado de los modelos: no se deshace.
    pass
