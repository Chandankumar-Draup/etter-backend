"""create master function table and update function table

Revision ID: 912854fa4a56
Revises: c4f8b9a12d56
Create Date: 2025-11-21 11:36:33.714288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '912854fa4a56'
down_revision: Union[str, None] = 'c4f8b9a12d56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('TRUNCATE TABLE etter.etter_workflowtask CASCADE')
    op.execute('TRUNCATE TABLE etter.etter_functionworkflow CASCADE')
    op.execute('TRUNCATE TABLE etter.etter_function CASCADE')
    
    op.create_table('etter_masterfunction',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('high_level_func', sa.String(length=200), nullable=False),
    sa.Column('sub_level_func', sa.String(length=200), nullable=False),
    sa.Column('updated_by', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('high_level_func', 'sub_level_func', name='uix_high_sub_level_func'),
    schema='etter'
    )
    op.add_column('etter_function', sa.Column('master_function_id', sa.Integer(), nullable=False), schema='etter')
    op.drop_constraint(op.f('uix_function_company'), 'etter_function', schema='etter', type_='unique')
    op.create_foreign_key(None, 'etter_function', 'etter_masterfunction', ['master_function_id'], ['id'], source_schema='etter', referent_schema='etter')
    op.drop_column('etter_function', 'function_name', schema='etter')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('etter_function', sa.Column('function_name', sa.VARCHAR(length=200), autoincrement=False, nullable=False), schema='etter')
    op.drop_constraint(None, 'etter_function', schema='etter', type_='foreignkey')
    op.create_unique_constraint(op.f('uix_function_company'), 'etter_function', ['function_name', 'company_id'], schema='etter', postgresql_nulls_not_distinct=False)
    op.drop_column('etter_function', 'master_function_id', schema='etter')
    op.drop_table('etter_masterfunction', schema='etter')
