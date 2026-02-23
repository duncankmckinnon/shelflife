"""float rating

Revision ID: b4d2f3a18c75
Revises: a3c7e1f09d42
Create Date: 2026-02-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4d2f3a18c75'
down_revision: Union[str, Sequence[str], None] = 'a3c7e1f09d42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('reviews') as batch_op:
        batch_op.alter_column('rating', type_=sa.Float(), existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('reviews') as batch_op:
        batch_op.alter_column('rating', type_=sa.Integer(), existing_nullable=True)
