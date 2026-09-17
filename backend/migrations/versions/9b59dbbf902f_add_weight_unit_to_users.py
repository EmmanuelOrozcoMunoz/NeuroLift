"""Add weight_unit (kg/lb) to users

Revision ID: 9b59dbbf902f
Revises: a4b5c6d7e8f9
Create Date: 2026-09-17

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "9b59dbbf902f"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("weight_unit", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "weight_unit")
