"""Add cover_image_filename to groups and mesocycles (plans)

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-09-10

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("groups", sa.Column("cover_image_filename", sa.String(length=255), nullable=True))
    op.add_column("mesocycles", sa.Column("cover_image_filename", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("mesocycles", "cover_image_filename")
    op.drop_column("groups", "cover_image_filename")
