"""add is_synthetic_fallback to roadmaps

Revision ID: aaabbb112233
Revises: cafaccd3c5ec
Create Date: 2026-07-12 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'aaabbb112233'
down_revision: Union[str, None] = 'cafaccd3c5ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('roadmaps', sa.Column('is_synthetic_fallback', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    op.drop_column('roadmaps', 'is_synthetic_fallback')
