"""task type

Revision ID: 9ff2afe0de2e
Revises: 54c3687efd04
Create Date: 2025-10-15 15:02:51.956215

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9ff2afe0de2e'
down_revision: Union[str, None] = '54c3687efd04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('etter_workflowtask', sa.Column('task_type', sa.String(length=25), nullable=True), schema='etter')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('etter_workflowtask', 'task_type', schema='etter')
