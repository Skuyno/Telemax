"""add message attachments

Revision ID: 7a3bfd6aec76
Revises: 2633f1f6392b
Create Date: 2026-09-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a3bfd6aec76'
down_revision: Union[str, Sequence[str], None] = '2633f1f6392b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'message_attachments',
        sa.Column('message_id', sa.Uuid(), nullable=False),
        sa.Column('file_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id']),
        sa.PrimaryKeyConstraint('message_id', 'file_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('message_attachments')
