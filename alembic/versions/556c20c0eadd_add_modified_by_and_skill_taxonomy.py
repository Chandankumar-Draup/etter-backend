"""add modified_by to role_taxonomy and create skill_taxonomy

Revision ID: add_modified_by_and_skill_taxonomy
Revises: b2c3d4e5f6a7
Create Date: 2025-12-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '556c20c0eadd'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('etter_role_taxonomy',
    sa.Column('modified_by', sa.Integer(), nullable=True),
    schema='etter'
    )
    
    op.create_foreign_key(
        'fk_role_taxonomy_modified_by',
        'etter_role_taxonomy', 'etter_users',
        ['modified_by'], ['id'],
        source_schema='etter', referent_schema='etter'
    )
    
    op.create_table('etter_master_skill_taxonomy_categories',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=250), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    schema='etter'
    )
    
    op.create_table('etter_skill_taxonomy',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('skill_id', sa.String(length=250), nullable=True),
    sa.Column('skill_name', sa.String(length=250), nullable=False),
    sa.Column('category', sa.String(length=250), nullable=True),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('proficiency_levels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('in_demand', sa.String(length=50), nullable=True, server_default='false'),
    sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
    sa.Column('draup_skill', sa.String(length=250), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('approver_id', sa.Integer(), nullable=True),
    sa.Column('modified_by', sa.Integer(), nullable=True),
    sa.Column('updated_on', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    sa.Column('approved_on', sa.DateTime(), nullable=True),
    sa.Column('modified_on', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    sa.Column('created_on', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('company_id', 'skill_name', name='uix_skill_taxonomy_company_skill_name'),
    schema='etter'
    )
    
    op.create_foreign_key(
        'fk_skill_taxonomy_company',
        'etter_skill_taxonomy', 'iris1_mastercompany',
        ['company_id'], ['id'],
        source_schema='etter', referent_schema='iris1'
    )
    op.create_foreign_key(
        'fk_skill_taxonomy_category',
        'etter_skill_taxonomy', 'etter_master_skill_taxonomy_categories',
        ['category_id'], ['id'],
        source_schema='etter', referent_schema='etter'
    )
    op.create_foreign_key(
        'fk_skill_taxonomy_user',
        'etter_skill_taxonomy', 'etter_users',
        ['user_id'], ['id'],
        source_schema='etter', referent_schema='etter'
    )
    op.create_foreign_key(
        'fk_skill_taxonomy_approver',
        'etter_skill_taxonomy', 'etter_users',
        ['approver_id'], ['id'],
        source_schema='etter', referent_schema='etter'
    )
    op.create_foreign_key(
        'fk_skill_taxonomy_modified_by',
        'etter_skill_taxonomy', 'etter_users',
        ['modified_by'], ['id'],
        source_schema='etter', referent_schema='etter'
    )


def downgrade() -> None:
    op.drop_constraint('fk_skill_taxonomy_modified_by', 'etter_skill_taxonomy', schema='etter', type_='foreignkey')
    op.drop_constraint('fk_skill_taxonomy_approver', 'etter_skill_taxonomy', schema='etter', type_='foreignkey')
    op.drop_constraint('fk_skill_taxonomy_user', 'etter_skill_taxonomy', schema='etter', type_='foreignkey')
    op.drop_constraint('fk_skill_taxonomy_category', 'etter_skill_taxonomy', schema='etter', type_='foreignkey')
    op.drop_constraint('fk_skill_taxonomy_company', 'etter_skill_taxonomy', schema='etter', type_='foreignkey')
    
    op.drop_table('etter_skill_taxonomy', schema='etter')
    op.drop_table('etter_master_skill_taxonomy_categories', schema='etter')
    
    op.drop_constraint('fk_role_taxonomy_modified_by', 'etter_role_taxonomy', schema='etter', type_='foreignkey')
    op.drop_column('etter_role_taxonomy', 'modified_by', schema='etter')
