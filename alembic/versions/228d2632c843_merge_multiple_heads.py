"""merge_multiple_heads

Revision ID: 228d2632c843
Revises: 20251210_143500, 30801977d4e4
Create Date: 2026-01-13 14:56:25.886121

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '228d2632c843'
down_revision: Union[str, None] = ('20251210_143500', '30801977d4e4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
