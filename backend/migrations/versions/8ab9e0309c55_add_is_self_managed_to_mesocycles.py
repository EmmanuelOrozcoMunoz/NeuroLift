"""Add is_self_managed to mesocycles

Revision ID: 8ab9e0309c55
Revises: 6af337bb3051
Create Date: 2026-09-21

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "8ab9e0309c55"
down_revision = "6af337bb3051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mesocycles",
        sa.Column("is_self_managed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("mesocycles", "is_self_managed")
