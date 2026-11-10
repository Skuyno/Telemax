"""add pins and message forwarding

Revision ID: c71e9a3d5f2b
Revises: b2f6a9d4c813
Create Date: 2026-11-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c71e9a3d5f2b'
down_revision: Union[str, Sequence[str], None] = 'b2f6a9d4c813'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'chat_settings',
        sa.Column('is_pinned', sa.Boolean(), server_default='false', nullable=False),
    )
    op.add_column(
        'chat_settings',
        sa.Column('pinned_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        'messages',
        sa.Column('forwarded_from_message_id', sa.Uuid(), nullable=True),
    )
    op.add_column(
        'messages',
        sa.Column('forwarded_from_sender_id', sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        'fk_messages_forwarded_from_message_id',
        'messages',
        'messages',
        ['forwarded_from_message_id'],
        ['id'],
    )

    op.create_table(
        'chat_message_pins',
        sa.Column('chat_id', sa.Uuid(), nullable=False),
        sa.Column('message_id', sa.Uuid(), nullable=False),
        sa.Column('pinned_by', sa.Uuid(), nullable=False),
        sa.Column('pinned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id']),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id']),
        sa.PrimaryKeyConstraint('chat_id', 'message_id'),
    )

    op.create_table(
        'message_pin_overrides',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('message_id', sa.Uuid(), nullable=False),
        sa.Column('chat_id', sa.Uuid(), nullable=False),
        sa.Column('state', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id']),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id']),
        sa.PrimaryKeyConstraint('user_id', 'message_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('message_pin_overrides')
    op.drop_table('chat_message_pins')
    op.drop_constraint('fk_messages_forwarded_from_message_id', 'messages', type_='foreignkey')
    op.drop_column('messages', 'forwarded_from_sender_id')
    op.drop_column('messages', 'forwarded_from_message_id')
    op.drop_column('chat_settings', 'pinned_at')
    op.drop_column('chat_settings', 'is_pinned')
