"""Add block_order and warmup_notes to sessions

Revision ID: 6af337bb3051
Revises: 1bead80f308f
Create Date: 2026-09-20

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "6af337bb3051"
down_revision = "1bead80f308f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("block_order", sa.String(length=200), nullable=True))
    op.add_column("sessions", sa.Column("warmup_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "warmup_notes")
    op.drop_column("sessions", "block_order")
