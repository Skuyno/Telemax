"""add message edit/delete and chat read state

Revision ID: 2633f1f6392b
Revises: d5d6506f04e2
Create Date: 2026-09-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2633f1f6392b'
down_revision: Union[str, Sequence[str], None] = 'd5d6506f04e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('messages', sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('messages', sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False))

    op.create_table(
        'chat_read_states',
        sa.Column('chat_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('last_read_message_id', sa.Uuid(), nullable=True),
        sa.Column('last_read_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id']),
        sa.ForeignKeyConstraint(['last_read_message_id'], ['messages.id']),
        sa.PrimaryKeyConstraint('chat_id', 'user_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('chat_read_states')
    op.drop_column('messages', 'is_deleted')
    op.drop_column('messages', 'edited_at')
