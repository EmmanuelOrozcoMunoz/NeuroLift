"""Add parent_session_id and duration_minutes to sessions (time-adapted sessions)

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-09-08

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("parent_session_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("sessions", sa.Column("duration_minutes", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "sessions_parent_session_id_fkey", "sessions", "sessions",
        ["parent_session_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_sessions_parent_session_id", "sessions", ["parent_session_id"])


def downgrade() -> None:
    op.drop_index("ix_sessions_parent_session_id", table_name="sessions")
    op.drop_constraint("sessions_parent_session_id_fkey", "sessions", type_="foreignkey")
    op.drop_column("sessions", "duration_minutes")
    op.drop_column("sessions", "parent_session_id")
