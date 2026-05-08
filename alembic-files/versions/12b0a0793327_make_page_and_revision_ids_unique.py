"""Make page and revision IDs unique

Revision ID: 12b0a0793327
Revises: 7ec78712ac95
Create Date: 2026-05-08 08:49:04.464794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12b0a0793327'
down_revision: Union[str, None] = '7ec78712ac95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint('unique_revision_id', 'declaration', ['revision_id'])
    op.create_unique_constraint('unique_page_id', 'declaration', ['page_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('unique_revision_id', 'declaration', type_='unique')
    op.drop_constraint('unique_page_id', 'declaration', type_='unique')
