"""Nota del coach por ejercicio: sets.coach_note

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-09-27

Solo agrega una columna opcional: no cambia datos existentes.
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b4c5d6e7f8a9"
down_revision = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sets", sa.Column("coach_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sets", "coach_note")
