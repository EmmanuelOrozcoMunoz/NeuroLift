"""Add missing FK indexes, set exercise_id ON DELETE SET NULL, drop insecure hashed_password default

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-09-06

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Índices en columnas FK consultadas frecuentemente (antes no existían)
    op.create_index("ix_mesocycles_user_id", "mesocycles", ["user_id"])
    op.create_index("ix_sessions_mesocycle_id", "sessions", ["mesocycle_id"])
    op.create_index("ix_sets_session_id", "sets", ["session_id"])
    op.create_index("ix_personal_records_user_id", "personal_records", ["user_id"])

    # sets.exercise_id no tenía ON DELETE definido: borrar un ejercicio fallaba
    # o dejaba huérfanos. Ahora, al borrar un ejercicio, sus sets quedan con
    # exercise_id = NULL en vez de romper la integridad referencial.
    op.drop_constraint("sets_exercise_id_fkey", "sets", type_="foreignkey")
    op.create_foreign_key(
        "sets_exercise_id_fkey", "sets", "exercises", ["exercise_id"], ["id"], ondelete="SET NULL"
    )

    # El default 'pass' en texto plano para hashed_password era un residuo
    # peligroso: cualquier INSERT que no pasara por la app quedaba con una
    # contraseña no-hasheada. La app siempre setea este campo explícitamente.
    op.alter_column("users", "hashed_password", server_default=None)


def downgrade() -> None:
    op.alter_column("users", "hashed_password", server_default="pass")

    op.drop_constraint("sets_exercise_id_fkey", "sets", type_="foreignkey")
    op.create_foreign_key("sets_exercise_id_fkey", "sets", "exercises", ["exercise_id"], ["id"])

    op.drop_index("ix_personal_records_user_id", table_name="personal_records")
    op.drop_index("ix_sets_session_id", table_name="sets")
    op.drop_index("ix_sessions_mesocycle_id", table_name="sessions")
    op.drop_index("ix_mesocycles_user_id", table_name="mesocycles")
