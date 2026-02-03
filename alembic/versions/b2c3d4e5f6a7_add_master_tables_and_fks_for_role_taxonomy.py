"""add master tables and fks for role taxonomy

Revision ID: b2c3d4e5f6a7
Revises: 553a170a5e45
Create Date: 2025-12-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = '553a170a5e45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('etter_master_company_role_management_level',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=250), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    schema='etter'
    )
    
    op.create_table('etter_master_company_role_job_track',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=250), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    schema='etter'
    )
    
    op.create_table('etter_master_company_role_job_family',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=250), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    schema='etter'
    )
    
    op.create_table('etter_master_company_role_occupation',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=250), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    schema='etter'
    )
    
    op.add_column('etter_role_taxonomy',
    sa.Column('occupation_id', sa.Integer(), nullable=True),
    schema='etter'
    )
    op.add_column('etter_role_taxonomy',
    sa.Column('job_family_id', sa.Integer(), nullable=True),
    schema='etter'
    )
    op.add_column('etter_role_taxonomy',
    sa.Column('job_track_id', sa.Integer(), nullable=True),
    schema='etter'
    )
    op.add_column('etter_role_taxonomy',
    sa.Column('management_level_id', sa.Integer(), nullable=True),
    schema='etter'
    )
    
    op.create_foreign_key(
        'fk_role_taxonomy_occupation',
        'etter_role_taxonomy', 'etter_master_company_role_occupation',
        ['occupation_id'], ['id'],
        source_schema='etter', referent_schema='etter'
    )
    op.create_foreign_key(
        'fk_role_taxonomy_job_family',
        'etter_role_taxonomy', 'etter_master_company_role_job_family',
        ['job_family_id'], ['id'],
        source_schema='etter', referent_schema='etter'
    )
    op.create_foreign_key(
        'fk_role_taxonomy_job_track',
        'etter_role_taxonomy', 'etter_master_company_role_job_track',
        ['job_track_id'], ['id'],
        source_schema='etter', referent_schema='etter'
    )
    op.create_foreign_key(
        'fk_role_taxonomy_management_level',
        'etter_role_taxonomy', 'etter_master_company_role_management_level',
        ['management_level_id'], ['id'],
        source_schema='etter', referent_schema='etter'
    )


def downgrade() -> None:
    op.drop_constraint('fk_role_taxonomy_management_level', 'etter_role_taxonomy', schema='etter', type_='foreignkey')
    op.drop_constraint('fk_role_taxonomy_job_track', 'etter_role_taxonomy', schema='etter', type_='foreignkey')
    op.drop_constraint('fk_role_taxonomy_job_family', 'etter_role_taxonomy', schema='etter', type_='foreignkey')
    op.drop_constraint('fk_role_taxonomy_occupation', 'etter_role_taxonomy', schema='etter', type_='foreignkey')
    
    op.drop_column('etter_role_taxonomy', 'management_level_id', schema='etter')
    op.drop_column('etter_role_taxonomy', 'job_track_id', schema='etter')
    op.drop_column('etter_role_taxonomy', 'job_family_id', schema='etter')
    op.drop_column('etter_role_taxonomy', 'occupation_id', schema='etter')
    
    op.drop_table('etter_master_company_role_occupation', schema='etter')
    op.drop_table('etter_master_company_role_job_family', schema='etter')
    op.drop_table('etter_master_company_role_job_track', schema='etter')
    op.drop_table('etter_master_company_role_management_level', schema='etter')
