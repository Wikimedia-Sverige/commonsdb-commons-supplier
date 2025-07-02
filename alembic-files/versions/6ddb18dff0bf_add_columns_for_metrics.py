"""Add columns for metrics

Revision ID: 6ddb18dff0bf
Revises: 7951804952de
Create Date: 2025-07-03 09:01:22.238446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ddb18dff0bf'
down_revision: Union[str, None] = '7951804952de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('declaration', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('declaration', sa.Column('download_time', sa.Float(), nullable=True))
    op.add_column('declaration', sa.Column('iscc_time', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('declaration', 'iscc_time')
    op.drop_column('declaration', 'download_time')
    op.drop_column('declaration', 'file_size')
