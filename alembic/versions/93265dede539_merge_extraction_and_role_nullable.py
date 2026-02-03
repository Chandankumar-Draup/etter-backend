"""merge_extraction_and_role_nullable

Revision ID: 93265dede539
Revises: af88634c8783, e9f1a2b3c4d5
Create Date: 2025-12-08 17:16:08.680272

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93265dede539'
down_revision: Union[str, None] = ('af88634c8783', 'e9f1a2b3c4d5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
