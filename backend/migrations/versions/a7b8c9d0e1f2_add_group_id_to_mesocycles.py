"""Link mesocycles to the group they were scheduled for (nullable)

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-09-07

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mesocycles", sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "mesocycles_group_id_fkey", "mesocycles", "groups", ["group_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_mesocycles_group_id", "mesocycles", ["group_id"])


def downgrade() -> None:
    op.drop_index("ix_mesocycles_group_id", table_name="mesocycles")
    op.drop_constraint("mesocycles_group_id_fkey", "mesocycles", type_="foreignkey")
    op.drop_column("mesocycles", "group_id")
