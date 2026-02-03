"""add_nullable_user_fk_for_extraction

Revision ID: f1a2b3c4d5e6
Revises: 93265dede539
Create Date: 2025-12-08 17:43:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = '93265dede539'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove FK constraint to allow extraction for users not in local DB."""
    # Drop the existing foreign key constraint
    op.drop_constraint(
        'etter_extraction_session_user_id_fkey',
        'etter_extraction_session',
        schema='etter',
        type_='foreignkey'
    )


def downgrade() -> None:
    """Restore FK constraint."""
    # Re-add the foreign key constraint
    op.create_foreign_key(
        'etter_extraction_session_user_id_fkey',
        'etter_extraction_session',
        'etter_users',
        ['user_id'],
        ['id'],
        source_schema='etter',
        referent_schema='etter'
    )
