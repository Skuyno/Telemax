"""add avatar_url to users

Revision ID: 3bcb8f5ec01b
Revises: 82ac3e19d573
Create Date: 2026-09-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3bcb8f5ec01b'
down_revision: Union[str, Sequence[str], None] = '82ac3e19d573'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('avatar_url', sa.String(length=512), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'avatar_url')
