"""add chat settings table

Revision ID: d5d6506f04e2
Revises: 47db32620621
Create Date: 2026-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5d6506f04e2'
down_revision: Union[str, Sequence[str], None] = '47db32620621'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'chat_settings',
        sa.Column('chat_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('notifications_muted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('chat_id', 'user_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('chat_settings')
