"""texonomy source fix

Revision ID: fe5b969914ba
Revises: d7253eaff019
Create Date: 2026-01-20 14:37:10.998517

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe5b969914ba'
down_revision: Union[str, None] = 'd7253eaff019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text("UPDATE etter.etter_role_taxonomy SET source = 'User' WHERE source = 'client_taxonomy'")
    )
    op.execute(
        sa.text("UPDATE etter.etter_skill_taxonomy SET source = 'User' WHERE source = 'client_taxonomy'")
    )
    op.execute(
        sa.text("UPDATE etter.etter_tech_stack_taxonomy SET source = 'User' WHERE source = 'client_taxonomy'")
    )
    op.alter_column('etter_role_taxonomy', 'source',
                    existing_type=sa.String(length=250),
                    server_default='User',
                    schema='etter')
    op.alter_column('etter_skill_taxonomy', 'source',
                    existing_type=sa.String(length=250),
                    server_default='User',
                    schema='etter')
    op.alter_column('etter_tech_stack_taxonomy', 'source',
                    existing_type=sa.String(length=250),
                    server_default='User',
                    schema='etter')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text("UPDATE etter.etter_role_taxonomy SET source = 'client_taxonomy' WHERE source = 'User'")
    )
    op.execute(
        sa.text("UPDATE etter.etter_skill_taxonomy SET source = 'client_taxonomy' WHERE source = 'User'")
    )
    op.execute(
        sa.text("UPDATE etter.etter_tech_stack_taxonomy SET source = 'client_taxonomy' WHERE source = 'User'")
    )
    op.alter_column('etter_role_taxonomy', 'source',
                    existing_type=sa.String(length=250),
                    server_default='client_taxonomy',
                    schema='etter')
    op.alter_column('etter_skill_taxonomy', 'source',
                    existing_type=sa.String(length=250),
                    server_default='client_taxonomy',
                    schema='etter')
    op.alter_column('etter_tech_stack_taxonomy', 'source',
                    existing_type=sa.String(length=250),
                    server_default='client_taxonomy',
                    schema='etter')
