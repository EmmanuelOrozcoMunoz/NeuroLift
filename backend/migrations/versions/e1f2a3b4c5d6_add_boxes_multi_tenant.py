"""Multi-box: tabla boxes + box_id en users, groups y planes

Revision ID: e1f2a3b4c5d6
Revises: 7c3b4e0ff063
Create Date: 2026-09-25

Todos los datos existentes (usuarios que no son admin de plataforma, grupos y planes) se mueven a
un box por defecto ya ACTIVO, para que nadie pierda acceso al aplicar la migración. Después, el
admin de plataforma puede renombrarlo desde el panel.
"""
import secrets
import uuid
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "e1f2a3b4c5d6"
down_revision = "7c3b4e0ff063"
branch_labels = None
depends_on = None

DEFAULT_BOX_NAME = "Mi box"
# Sin 0/O ni 1/I: el código se dicta en voz alta o se copia de una pantalla
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def upgrade() -> None:
    op.create_table(
        "boxes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("logo_filename", sa.String(length=255), nullable=True),
        sa.Column("accent_color", sa.String(length=7), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("invite_code", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_boxes_invite_code", "boxes", ["invite_code"], unique=True)

    op.add_column("users", sa.Column("box_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_users_box_id", "users", "boxes", ["box_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_users_box_id", "users", ["box_id"])

    op.add_column("groups", sa.Column("box_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_groups_box_id", "groups", "boxes", ["box_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_groups_box_id", "groups", ["box_id"])

    op.add_column("mesocycles", sa.Column("box_id", UUID(as_uuid=True), nullable=True))
    op.add_column(
        "mesocycles", sa.Column("plan_visibility", sa.String(length=10), nullable=False, server_default="box")
    )
    op.create_foreign_key("fk_mesocycles_box_id", "mesocycles", "boxes", ["box_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_mesocycles_box_id", "mesocycles", ["box_id"])

    # --- Datos existentes -> box por defecto ---
    conn = op.get_bind()
    hay_datos = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM users WHERE role <> 'admin')")).scalar()
    if not hay_datos:
        return

    box_id = uuid.uuid4()
    ahora = datetime.utcnow()
    conn.execute(
        sa.text(
            "INSERT INTO boxes (id, name, status, invite_code, created_at, approved_at) "
            "VALUES (:id, :name, 'active', :code, :now, :now)"
        ),
        {
            "id": box_id,
            "name": DEFAULT_BOX_NAME,
            "code": "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8)),
            "now": ahora,
        },
    )
    conn.execute(sa.text("UPDATE users SET box_id = :b WHERE role <> 'admin'"), {"b": box_id})
    conn.execute(sa.text("UPDATE groups SET box_id = :b"), {"b": box_id})
    # Planes (plantillas): conservan el comportamiento de antes — el catálogo era global, así que
    # los que ya estaban publicados quedan públicos para no desaparecer de la vista de nadie.
    conn.execute(
        sa.text(
            "UPDATE mesocycles SET box_id = :b, "
            "plan_visibility = CASE WHEN is_published THEN 'public' ELSE 'box' END "
            "WHERE is_template = true"
        ),
        {"b": box_id},
    )


def downgrade() -> None:
    op.drop_index("ix_mesocycles_box_id", table_name="mesocycles")
    op.drop_constraint("fk_mesocycles_box_id", "mesocycles", type_="foreignkey")
    op.drop_column("mesocycles", "plan_visibility")
    op.drop_column("mesocycles", "box_id")

    op.drop_index("ix_groups_box_id", table_name="groups")
    op.drop_constraint("fk_groups_box_id", "groups", type_="foreignkey")
    op.drop_column("groups", "box_id")

    # Un "owner" sin tabla de boxes no tiene sentido: vuelve a ser coach
    op.execute("UPDATE users SET role = 'coach' WHERE role = 'owner'")
    op.drop_index("ix_users_box_id", table_name="users")
    op.drop_constraint("fk_users_box_id", "users", type_="foreignkey")
    op.drop_column("users", "box_id")

    op.drop_index("ix_boxes_invite_code", table_name="boxes")
    op.drop_table("boxes")
