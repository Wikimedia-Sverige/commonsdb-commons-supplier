"""change CID field name to match new API response

Revision ID: 7ec78712ac95
Revises: bdf40c0c3729
Create Date: 2026-01-09 09:02:59.987484

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7ec78712ac95'
down_revision: Union[str, None] = 'bdf40c0c3729'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('declaration', sa.Column('cid', sa.String(length=57), nullable=True))
    op.drop_column('declaration', 'ingested_cid')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('declaration', sa.Column('ingested_cid', sa.String(length=57), nullable=True))
    op.drop_column('declaration', 'cid')
