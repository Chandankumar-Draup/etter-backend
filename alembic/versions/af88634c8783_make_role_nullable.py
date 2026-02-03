"""make_role_nullable

Revision ID: af88634c8783
Revises: 20251128_153910
Create Date: 2025-12-02 12:01:01.154461

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af88634c8783'
down_revision: Union[str, None] = '20251128_153910'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make role column nullable for filesystem mode support."""
    op.alter_column('s3_documents', 'role',
                    existing_type=sa.String(length=255),
                    nullable=True,
                    schema='etter')


def downgrade() -> None:
    """Make role column non-nullable again."""
    # First set empty roles to a default value
    op.execute("UPDATE etter.s3_documents SET role = 'unknown' WHERE role IS NULL")

    op.alter_column('s3_documents', 'role',
                    existing_type=sa.String(length=255),
                    nullable=False,
                    schema='etter')
