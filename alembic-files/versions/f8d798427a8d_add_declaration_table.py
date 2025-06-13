"""Add declaration table

Revision ID: f8d798427a8d
Revises: 
Create Date: 2025-06-13 10:56:25.776161

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f8d798427a8d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('declaration',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('page_id', sa.Integer(), nullable=False),
    sa.Column('revision_id', sa.Integer(), nullable=False),
    sa.Column('image_hash', sa.String(length=41), nullable=True),
    sa.Column('iscc', sa.String(length=61), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('declaration')
