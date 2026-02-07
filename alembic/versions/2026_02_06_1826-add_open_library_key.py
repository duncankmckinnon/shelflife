"""add open library key

Revision ID: f8821bef4b4e
Revises: cb08291de4c9
Create Date: 2026-02-06 18:26:25.375349

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8821bef4b4e'
down_revision: Union[str, Sequence[str], None] = 'cb08291de4c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('books', sa.Column('open_library_key', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('books', 'open_library_key')
