"""Ranking del box: users.show_in_ranking

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-09-29

Cada atleta decide si aparece en el ranking de su box (por defecto sí). Aditiva y tolerante a
que la columna ya exista (create_all la crea en un ambiente nuevo).
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c5d6e7f8a9b0"
down_revision = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def _tiene_columna() -> bool:
    columnas = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}
    return "show_in_ranking" in columnas


def upgrade() -> None:
    if not _tiene_columna():
        op.add_column(
            "users",
            sa.Column("show_in_ranking", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )


def downgrade() -> None:
    if _tiene_columna():
        op.drop_column("users", "show_in_ranking")
