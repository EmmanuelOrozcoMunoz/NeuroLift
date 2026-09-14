"""Add category (rx/scaled) to users

Revision ID: a4b5c6d7e8f9
Revises: d2e3f4a5b6c7
Create Date: 2026-09-14

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a4b5c6d7e8f9"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("category", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "category")
