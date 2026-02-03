"""merge_heads

Revision ID: 9e9e90171fbb
Revises: 8c5278b962e8, e78e7200800f
Create Date: 2025-10-09 11:44:24.817840

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e9e90171fbb'
down_revision: Union[str, None] = ('8c5278b962e8', 'e78e7200800f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
