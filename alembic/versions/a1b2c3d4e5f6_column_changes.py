"""column changes

Revision ID: a1b2c3d4e5f6
Revises: dd3e7d39a9aa
Create Date: 2025-12-26 12:09:29.183851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'dd3e7d39a9aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('etter_users', 'image',
               existing_type=sa.Text(),
               type_=sa.String(length=400),
               existing_nullable=True,
               schema='etter')


def downgrade() -> None:
    op.alter_column('etter_users', 'image',
               existing_type=sa.String(length=400),
               type_=sa.Text(),
               existing_nullable=True,
               schema='etter')

