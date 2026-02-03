"""fix_extracted_document_modified_on_default

Revision ID: a1b2c3d4e5f7
Revises: fae096832ade
Create Date: 2026-01-22 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'fae096832ade'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('etter_extracted_document', 'modified_on',
                   existing_type=sa.DateTime(),
                   server_default=sa.text('now()'),
                   nullable=False,
                   schema='etter')


def downgrade() -> None:
    op.alter_column('etter_extracted_document', 'modified_on',
                   existing_type=sa.DateTime(),
                   server_default=None,
                   nullable=False,
                   schema='etter')
