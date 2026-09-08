"""Add fitness_benchmarks table (Fit Level calculator)

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-09-08

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fitness_benchmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_key", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_fitness_benchmarks_user_id", "fitness_benchmarks", ["user_id"])
    op.create_unique_constraint(
        "uq_fitness_benchmark_user_metric", "fitness_benchmarks", ["user_id", "metric_key"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_fitness_benchmark_user_metric", "fitness_benchmarks", type_="unique")
    op.drop_index("ix_fitness_benchmarks_user_id", table_name="fitness_benchmarks")
    op.drop_table("fitness_benchmarks")
