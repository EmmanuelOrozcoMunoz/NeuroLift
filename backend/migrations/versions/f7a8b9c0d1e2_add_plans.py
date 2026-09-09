"""Add plan templates (sellable plans): template flags on mesocycles, day_offset on sessions,
percentage-based loads on sets

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-09-09

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- mesocycles: metadata de plantilla/catálogo ---
    op.add_column("mesocycles", sa.Column("is_template", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("mesocycles", sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("mesocycles", sa.Column("created_by_coach_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("mesocycles", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("mesocycles", sa.Column("level", sa.String(length=20), nullable=True))
    op.add_column("mesocycles", sa.Column("price", sa.Float(), nullable=True))
    op.add_column("mesocycles", sa.Column("source_plan_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "mesocycles_created_by_coach_id_fkey", "mesocycles", "users",
        ["created_by_coach_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "mesocycles_source_plan_id_fkey", "mesocycles", "mesocycles",
        ["source_plan_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_mesocycles_created_by_coach_id", "mesocycles", ["created_by_coach_id"])

    # --- sessions: día relativo dentro del plan ---
    op.add_column("sessions", sa.Column("day_offset", sa.Integer(), nullable=True))

    # --- sets: carga en % de 1RM (se resuelve a kg al adquirir el plan) ---
    op.add_column("sets", sa.Column("prescribed_percentage", sa.Float(), nullable=True))
    op.add_column("sets", sa.Column("reference_exercise", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("sets", "reference_exercise")
    op.drop_column("sets", "prescribed_percentage")
    op.drop_column("sessions", "day_offset")
    op.drop_index("ix_mesocycles_created_by_coach_id", table_name="mesocycles")
    op.drop_constraint("mesocycles_source_plan_id_fkey", "mesocycles", type_="foreignkey")
    op.drop_constraint("mesocycles_created_by_coach_id_fkey", "mesocycles", type_="foreignkey")
    op.drop_column("mesocycles", "source_plan_id")
    op.drop_column("mesocycles", "price")
    op.drop_column("mesocycles", "level")
    op.drop_column("mesocycles", "description")
    op.drop_column("mesocycles", "created_by_coach_id")
    op.drop_column("mesocycles", "is_published")
    op.drop_column("mesocycles", "is_template")
