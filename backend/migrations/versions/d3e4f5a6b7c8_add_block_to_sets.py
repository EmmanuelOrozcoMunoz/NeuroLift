"""Add block to sets (warmup/strength/weightlifting/skills/metcon/accessory/main)

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-09-10

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sets", sa.Column("block", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("sets", "block")
