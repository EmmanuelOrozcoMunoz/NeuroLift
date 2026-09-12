"""Add WOD/metcon result fields to sessions (for_time/amrap/emom/1rm)

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-09-12

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("wod_format", sa.String(length=20), nullable=True))
    op.add_column("sessions", sa.Column("wod_time_seconds", sa.Integer(), nullable=True))
    op.add_column("sessions", sa.Column("wod_rounds", sa.Integer(), nullable=True))
    op.add_column("sessions", sa.Column("wod_extra_reps", sa.Integer(), nullable=True))
    op.add_column("sessions", sa.Column("wod_emom_completed", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "wod_emom_completed")
    op.drop_column("sessions", "wod_extra_reps")
    op.drop_column("sessions", "wod_rounds")
    op.drop_column("sessions", "wod_time_seconds")
    op.drop_column("sessions", "wod_format")
