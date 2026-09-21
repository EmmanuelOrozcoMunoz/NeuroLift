"""add wod_notes to sessions

Revision ID: bc48a974c56c
Revises: 8ab9e0309c55
Create Date: 2026-09-20 20:30:20.325114

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc48a974c56c'
down_revision: Union[str, Sequence[str], None] = '8ab9e0309c55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("sessions", sa.Column("wod_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("sessions", "wod_notes")
