"""add ingested_cid to keep track of when a declaration was successfully added

Revision ID: bdf40c0c3729
Revises: 20262d93dd61
Create Date: 2025-08-21 08:59:16.549982

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bdf40c0c3729'
down_revision: Union[str, None] = '20262d93dd61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('declaration', sa.Column('ingested_cid', sa.String(length=57), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('declaration', 'ingested_cid')
