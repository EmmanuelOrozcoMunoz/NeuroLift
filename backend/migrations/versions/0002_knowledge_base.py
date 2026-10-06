"""Tabla knowledge_base (literatura para la IA, búsqueda vectorial con pgvector).

No es un modelo de SQLAlchemy: la usan consultas SQL crudas (backend/knowledge_search.py y
backend/knowledge/cargar_pdf.py), por eso Alembic no la detecta sola. Se crea solo si la base
ofrece la extensión `vector` (Supabase sí; el Postgres descartable del CI no). Sin ella la
búsqueda falla en silencio y la IA genera sin literatura, como ya hacía.

Revision ID: 0002
Revises: 0001
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            CREATE EXTENSION IF NOT EXISTS vector;
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id bigserial PRIMARY KEY,
                source_name text,
                content text NOT NULL,
                embedding vector(768)
            );
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'pgvector no disponible (%): se omite knowledge_base', SQLERRM;
        END
        $$;
    """)


def downgrade() -> None:
    # No se borra: puede traer literatura cargada a mano con cargar_pdf.py.
    pass
