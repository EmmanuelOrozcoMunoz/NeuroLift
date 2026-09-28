"""Clases del box: tabla box_classes, class_id/is_class_log en mesocycles y class_session_id en sessions

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-09-27

Solo agrega estructura: no mueve ni cambia datos existentes. Tolera que box_classes ya exista
(creada por create_all() de main.py antes de correr la migración).
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "a3b4c5d6e7f8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # main.py llama a Base.metadata.create_all() al arrancar: si un backend con este código se
    # levantó antes de migrar, box_classes ya existe (idéntica y vacía) pero las columnas nuevas
    # de mesocycles/sessions no — create_all no altera tablas existentes. En ese caso solo se
    # salta la creación de la tabla.
    if not sa.inspect(op.get_bind()).has_table("box_classes"):
        _create_box_classes()

    _add_class_columns()


def _create_box_classes() -> None:
    op.create_table(
        "box_classes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("box_id", UUID(as_uuid=True), sa.ForeignKey("boxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("coach_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("weekdays", sa.String(length=20), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_box_classes_box_id", "box_classes", ["box_id"])
    op.create_index("ix_box_classes_coach_id", "box_classes", ["coach_id"])


def _add_class_columns() -> None:
    op.add_column("mesocycles", sa.Column("class_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_mesocycles_class_id", "mesocycles", "box_classes", ["class_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_mesocycles_class_id", "mesocycles", ["class_id"])
    op.add_column(
        "mesocycles", sa.Column("is_class_log", sa.Boolean(), nullable=False, server_default="false")
    )

    op.add_column("sessions", sa.Column("class_session_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_sessions_class_session_id", "sessions", "sessions", ["class_session_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_sessions_class_session_id", "sessions", ["class_session_id"])


def downgrade() -> None:
    op.drop_index("ix_sessions_class_session_id", table_name="sessions")
    op.drop_constraint("fk_sessions_class_session_id", "sessions", type_="foreignkey")
    op.drop_column("sessions", "class_session_id")

    op.drop_column("mesocycles", "is_class_log")
    op.drop_index("ix_mesocycles_class_id", table_name="mesocycles")
    op.drop_constraint("fk_mesocycles_class_id", "mesocycles", type_="foreignkey")
    op.drop_column("mesocycles", "class_id")

    op.drop_index("ix_box_classes_coach_id", table_name="box_classes")
    op.drop_index("ix_box_classes_box_id", table_name="box_classes")
    op.drop_table("box_classes")
