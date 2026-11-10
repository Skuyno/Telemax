"""add message replies

Revision ID: e4a8c3f71d6b
Revises: c71e9a3d5f2b
Create Date: 2026-11-10 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4a8c3f71d6b'
down_revision: Union[str, Sequence[str], None] = 'c71e9a3d5f2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'messages',
        sa.Column('reply_to_message_id', sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        'fk_messages_reply_to_message_id',
        'messages',
        'messages',
        ['reply_to_message_id'],
        ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_messages_reply_to_message_id', 'messages', type_='foreignkey')
    op.drop_column('messages', 'reply_to_message_id')
