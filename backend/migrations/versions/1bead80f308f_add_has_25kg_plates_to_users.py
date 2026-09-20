"""Add has_25kg_plates to users

Revision ID: 1bead80f308f
Revises: 9b59dbbf902f
Create Date: 2026-09-20

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "1bead80f308f"
down_revision = "9b59dbbf902f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("has_25kg_plates", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "has_25kg_plates")
