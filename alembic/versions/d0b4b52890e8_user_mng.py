"""user mng

Revision ID: d0b4b52890e8
Revises: e217ec738b3d
Create Date: 2025-08-13 11:25:12.155299

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd0b4b52890e8'
down_revision: Union[str, None] = 'e217ec738b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns to MasterCompany table
    op.add_column('iris1_mastercompany', sa.Column('light_theme_image', sa.Text(), nullable=True), schema='iris1')
    op.add_column('iris1_mastercompany', sa.Column('dark_theme_image', sa.Text(), nullable=True), schema='iris1')

    # Update the enum type - this automatically updates all existing data
    op.execute("ALTER TYPE user_group_type RENAME VALUE 'User' TO 'Researcher'")
    op.execute("ALTER TYPE user_group_type RENAME VALUE 'Approver' TO 'Reviewer'")


def downgrade() -> None:
    """Downgrade schema."""
    # Remove columns from MasterCompany table
    op.drop_column('iris1_mastercompany', 'dark_theme_image', schema='iris1')
    op.drop_column('iris1_mastercompany', 'light_theme_image', schema='iris1')

    # Revert the enum type - this automatically updates all existing data
    op.execute("ALTER TYPE user_group_type RENAME VALUE 'Researcher' TO 'User'")
    op.execute("ALTER TYPE user_group_type RENAME VALUE 'Reviewer' TO 'Approver'")
