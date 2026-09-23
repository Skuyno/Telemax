"""add phone to users

Revision ID: 82ac3e19d573
Revises: deac91b0f3e7
Create Date: 2026-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82ac3e19d573'
down_revision: Union[str, Sequence[str], None] = 'deac91b0f3e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('phone', sa.String(length=32), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'phone')
