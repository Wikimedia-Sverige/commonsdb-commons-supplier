"""fix typo

Revision ID: fcabcc2708d6
Revises: 12b0a0793327
Create Date: 2026-07-16 15:17:45.218675

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fcabcc2708d6'
down_revision: Union[str, None] = '12b0a0793327'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'tag_association',
        'declartion_id',
        new_column_name='declaration_id',
        existing_type=sa.Integer(),
        existing_nullable=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'tag_association',
        'declaration_id',
        new_column_name='declartion_id',
        existing_type=sa.Integer(),
        existing_nullable=False
    )
