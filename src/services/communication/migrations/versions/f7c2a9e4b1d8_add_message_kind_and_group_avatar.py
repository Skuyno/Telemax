"""add message kind and group avatar

Revision ID: f7c2a9e4b1d8
Revises: e4a8c3f71d6b
Create Date: 2026-11-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7c2a9e4b1d8'
down_revision: Union[str, Sequence[str], None] = 'e4a8c3f71d6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'messages',
        sa.Column('kind', sa.String(length=16), server_default='text', nullable=False),
    )
    op.add_column(
        'messages',
        sa.Column('service_action', sa.String(length=32), nullable=True),
    )
    op.add_column(
        'messages',
        sa.Column('service_target_message_id', sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        'fk_messages_service_target_message_id',
        'messages',
        'messages',
        ['service_target_message_id'],
        ['id'],
    )

    op.add_column(
        'group_chats',
        sa.Column('avatar_url', sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('group_chats', 'avatar_url')

    op.drop_constraint(
        'fk_messages_service_target_message_id', 'messages', type_='foreignkey'
    )
    op.drop_column('messages', 'service_target_message_id')
    op.drop_column('messages', 'service_action')
    op.drop_column('messages', 'kind')
