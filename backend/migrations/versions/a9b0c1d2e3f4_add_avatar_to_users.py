"""Add avatar_filename to users (profile photo, stored on disk outside the web root)

Revision ID: a9b0c1d2e3f4
Revises: f7a8b9c0d1e2
Create Date: 2026-09-10

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a9b0c1d2e3f4"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_filename", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_filename")
