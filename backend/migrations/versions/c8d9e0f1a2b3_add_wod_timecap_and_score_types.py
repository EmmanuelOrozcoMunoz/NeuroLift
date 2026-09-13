"""Add WOD time cap and calories/distance/watts score fields to sessions

Revision ID: c8d9e0f1a2b3
Revises: f5a6b7c8d9e0
Create Date: 2026-09-13

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c8d9e0f1a2b3"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("wod_time_cap_seconds", sa.Integer(), nullable=True))
    op.add_column("sessions", sa.Column("wod_calories", sa.Float(), nullable=True))
    op.add_column("sessions", sa.Column("wod_distance_meters", sa.Float(), nullable=True))
    op.add_column("sessions", sa.Column("wod_watts", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "wod_watts")
    op.drop_column("sessions", "wod_distance_meters")
    op.drop_column("sessions", "wod_calories")
    op.drop_column("sessions", "wod_time_cap_seconds")
