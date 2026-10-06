"""Alinea con los modelos las bases creadas ANTES de la migración base (Dev y QA).

Esas bases nacieron de un esquema original y de `create_all()`, y arrastran diferencias con
backend/models.py: pesos de las series como NUMERIC (los modelos usan Float), una columna
`sessions.wod_name` que ya no existe, un índice con otro nombre y el correo único como
constraint en vez de índice. Cada paso se aplica solo si hace falta: en una base nueva (creada
por 0001) esta migración no cambia nada.

Revision ID: 0003
Revises: 0002
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tipo(insp, tabla: str, columna: str):
    return next((c["type"] for c in insp.get_columns(tabla) if c["name"] == columna), None)


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    # Pesos y puntaje de técnica: NUMERIC(6,2)/(3,2) -> Float (como el modelo). Ensancha el tipo,
    # no pierde valores.
    for tabla, columna in (("sets", "prescribed_weight"), ("sets", "actual_weight"), ("sets", "technique_score")):
        if isinstance(_tipo(insp, tabla, columna), sa.Numeric) and not isinstance(_tipo(insp, tabla, columna), sa.Float):
            op.alter_column(tabla, columna, type_=sa.Float(), existing_nullable=True,
                            postgresql_using=f"{columna}::double precision")

    # Columna que ya no existe en los modelos (nadie la lee ni la escribe).
    if _tipo(insp, "sessions", "wod_name") is not None:
        op.drop_column("sessions", "wod_name")

    # Índice de PersonalRecord.exercise_name con el nombre que Alembic espera.
    indices = {i["name"] for i in insp.get_indexes("personal_records")}
    if "idx_personal_records_exercise_name" in indices and "ix_personal_records_exercise_name" not in indices:
        op.execute("ALTER INDEX idx_personal_records_exercise_name RENAME TO ix_personal_records_exercise_name")

    # users.email: único por INDEX (ix_users_email), no por constraint.
    indices_u = {i["name"] for i in insp.get_indexes("users")}
    if "ix_users_email" not in indices_u:
        for uc in insp.get_unique_constraints("users"):
            if uc["column_names"] == ["email"]:
                op.drop_constraint(uc["name"], "users", type_="unique")
        op.create_index("ix_users_email", "users", ["email"], unique=True)
    if "ix_users_full_name" not in indices_u:
        op.create_index("ix_users_full_name", "users", ["full_name"], unique=False)


def downgrade() -> None:
    # Solo acerca la base al estado de los modelos: no se deshace (no hay nada que restaurar).
    pass
