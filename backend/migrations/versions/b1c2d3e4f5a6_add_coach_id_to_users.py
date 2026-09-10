"""Add coach_id to users (scope each coach to their own athletes)

Revision ID: b1c2d3e4f5a6
Revises: a9b0c1d2e3f4
Create Date: 2026-09-10

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("coach_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("users_coach_id_fkey", "users", "users", ["coach_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_users_coach_id", "users", ["coach_id"])


def downgrade() -> None:
    op.drop_index("ix_users_coach_id", table_name="users")
    op.drop_constraint("users_coach_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "coach_id")
