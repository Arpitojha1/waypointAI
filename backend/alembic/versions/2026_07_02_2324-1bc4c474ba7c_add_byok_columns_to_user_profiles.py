"""add byok columns to user_profiles

Revision ID: 1bc4c474ba7c
Revises: 001_initial_schema
Create Date: 2026-07-02 23:24:02.836075

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1bc4c474ba7c'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('byok_key_encrypted', sa.LargeBinary(), nullable=True))
    op.add_column('user_profiles', sa.Column('byok_model', sa.String(length=255), nullable=True))
    op.add_column('user_profiles', sa.Column('byok_endpoint', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('user_profiles', 'byok_endpoint')
    op.drop_column('user_profiles', 'byok_model')
    op.drop_column('user_profiles', 'byok_key_encrypted')
