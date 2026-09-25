"""Coaches independientes y suscripciones: kind, plan, trial_ends_at y paid_until en boxes

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-09-25

Las cuentas que ya existen quedan como boxes (kind="box") en el plan básico, con 14 días de
prueba a partir de hoy: así nadie queda "vencido" en el momento de aplicar la migración, y el
admin tiene dos semanas para asignar el plan correcto y registrar el primer pago.
"""
from datetime import datetime, timedelta

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None

TRIAL_DAYS = 14


def upgrade() -> None:
    op.add_column("boxes", sa.Column("kind", sa.String(length=10), nullable=False, server_default="box"))
    op.add_column("boxes", sa.Column("plan", sa.String(length=20), nullable=False, server_default="basic"))
    op.add_column("boxes", sa.Column("trial_ends_at", sa.DateTime(), nullable=True))
    op.add_column("boxes", sa.Column("paid_until", sa.DateTime(), nullable=True))
    op.get_bind().execute(
        sa.text("UPDATE boxes SET trial_ends_at = :fin"),
        {"fin": datetime.utcnow() + timedelta(days=TRIAL_DAYS)},
    )


def downgrade() -> None:
    op.drop_column("boxes", "paid_until")
    op.drop_column("boxes", "trial_ends_at")
    op.drop_column("boxes", "plan")
    op.drop_column("boxes", "kind")
