"""add_taxonomy_role_associations

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-01-22 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a8'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'etter_skill_taxonomy_role_association',
        sa.Column('skill_taxonomy_id', sa.Integer(), nullable=False),
        sa.Column('role_taxonomy_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['skill_taxonomy_id'], ['etter.etter_skill_taxonomy.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_taxonomy_id'], ['etter.etter_role_taxonomy.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('skill_taxonomy_id', 'role_taxonomy_id'),
        schema='etter'
    )
    
    op.create_table(
        'etter_tech_stack_taxonomy_role_association',
        sa.Column('tech_stack_taxonomy_id', sa.Integer(), nullable=False),
        sa.Column('role_taxonomy_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['tech_stack_taxonomy_id'], ['etter.etter_tech_stack_taxonomy.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_taxonomy_id'], ['etter.etter_role_taxonomy.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tech_stack_taxonomy_id', 'role_taxonomy_id'),
        schema='etter'
    )


def downgrade() -> None:
    op.drop_table('etter_tech_stack_taxonomy_role_association', schema='etter')
    op.drop_table('etter_skill_taxonomy_role_association', schema='etter')
