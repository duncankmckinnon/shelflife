"""add reading tracking

Revision ID: a3c7e1f09d42
Revises: f8821bef4b4e
Create Date: 2026-02-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c7e1f09d42'
down_revision: Union[str, Sequence[str], None] = 'f8821bef4b4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'readings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.Date(), nullable=True),
        sa.Column('finished_at', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_readings_book_id', 'readings', ['book_id'])

    op.create_table(
        'reading_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reading_id', sa.Integer(), nullable=False),
        sa.Column('page', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['reading_id'], ['readings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reading_id', 'date'),
    )
    op.create_index('ix_reading_progress_reading_id', 'reading_progress', ['reading_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_reading_progress_reading_id', 'reading_progress')
    op.drop_table('reading_progress')
    op.drop_index('ix_readings_book_id', 'readings')
    op.drop_table('readings')
