"""add role to users

Revision ID: f4a1c6e9d2b7
Revises: 3bcb8f5ec01b
Create Date: 2026-09-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a1c6e9d2b7'
down_revision: Union[str, Sequence[str], None] = '3bcb8f5ec01b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column('role', sa.String(length=16), nullable=False, server_default='user'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'role')
