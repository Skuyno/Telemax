"""add user settings table

Revision ID: deac91b0f3e7
Revises: 324bc9080ed3
Create Date: 2026-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'deac91b0f3e7'
down_revision: Union[str, Sequence[str], None] = '324bc9080ed3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'user_settings',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('notifications_enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('accept_calls', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('user_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user_settings')
