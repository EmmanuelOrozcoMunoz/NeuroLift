"""Drop users.bodyweight (columna huerfana, duplicada de body_weight)

users.bodyweight (numeric) nunca estuvo en el modelo de SQLAlchemy ni en ninguna migracion
anterior -- quedo de una iteracion muy temprana de la tabla, antes de Alembic, cuando el campo
se llamo asi antes de renombrarse a body_weight. Confirmado vacio (NULL) en los 10 usuarios
reales antes de borrarla, asi que no se pierde ningun dato.

users.created_at SI se queda (ya existia en la tabla real con datos buenos desde el principio;
solo le faltaba estar declarada en el modelo -- eso se resolvio en models.py, no aqui).

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-09-12

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "bodyweight")


def downgrade() -> None:
    op.add_column("users", sa.Column("bodyweight", sa.Numeric(), nullable=True))
