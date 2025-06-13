"""Add column for update timestamp

Revision ID: 7951804952de
Revises: f8d798427a8d
Create Date: 2025-06-13 14:23:56.663462

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '7951804952de'
down_revision: Union[str, None] = 'f8d798427a8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('declaration', 'timestamp', existing_type=sa.DateTime(), existing_nullable=False, new_column_name='created_timestamp')
    op.add_column('declaration', sa.Column('updated_timestamp', sa.DateTime(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('declaration', 'created_timestamp', existing_type=sa.DateTime(), existing_nullable=False, new_column_name='timestamp')
    op.drop_column('declaration', 'updated_timestamp')
