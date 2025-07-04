"""Add width and height for files

Revision ID: 20262d93dd61
Revises: 626dc7b4c638
Create Date: 2025-07-04 10:54:06.289904

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20262d93dd61'
down_revision: Union[str, None] = '626dc7b4c638'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('declaration', sa.Column('width', sa.Integer(), nullable=True))
    op.add_column('declaration', sa.Column('height', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('declaration', 'height')
    op.drop_column('declaration', 'width')
