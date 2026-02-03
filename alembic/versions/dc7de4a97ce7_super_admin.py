"""super_admin

Revision ID: dc7de4a97ce7
Revises: d0b4b52890e8
Create Date: 2025-08-14 10:57:29.414888

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'dc7de4a97ce7'
down_revision: Union[str, None] = 'd0b4b52890e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    connection = op.get_bind()
    
    result = connection.execute(sa.text("SELECT unnest(enum_range(NULL::user_group_type))"))
    existing_values = [row[0] for row in result.fetchall()]
    
    if 'Super Admin' not in existing_values:
        connection.execute(sa.text("ALTER TYPE user_group_type ADD VALUE 'Super Admin'"))


def downgrade() -> None:
    """Downgrade schema."""
    pass
