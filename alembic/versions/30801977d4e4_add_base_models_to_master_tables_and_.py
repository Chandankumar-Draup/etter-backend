"""add_base_models_to_master_tables_and_tech_stack_taxonomy

Revision ID: 30801977d4e4
Revises: f569ffbc9096
Create Date: 2026-01-13 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30801977d4e4'
down_revision: Union[str, None] = 'f569ffbc9096'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    op.add_column('etter_master_company_role_occupation',
                  sa.Column('created_by', sa.String(length=255), nullable=True),
                  schema='etter')
    op.add_column('etter_master_company_role_occupation',
                  sa.Column('modified_by', sa.String(length=255), nullable=True),
                  schema='etter')
    op.add_column('etter_master_company_role_occupation',
                  sa.Column('created_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
                  schema='etter')
    op.add_column('etter_master_company_role_occupation',
                  sa.Column('modified_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
                  schema='etter')
    op.drop_column('etter_master_company_role_occupation', 'created_at', schema='etter')
    op.drop_column('etter_master_company_role_occupation', 'updated_at', schema='etter')
    
    op.add_column('etter_master_company_role_job_family',
                  sa.Column('created_by', sa.String(length=255), nullable=True),
                  schema='etter')
    op.add_column('etter_master_company_role_job_family',
                  sa.Column('modified_by', sa.String(length=255), nullable=True),
                  schema='etter')
    op.add_column('etter_master_company_role_job_family',
                  sa.Column('created_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
                  schema='etter')
    op.add_column('etter_master_company_role_job_family',
                  sa.Column('modified_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
                  schema='etter')
    op.drop_column('etter_master_company_role_job_family', 'created_at', schema='etter')
    op.drop_column('etter_master_company_role_job_family', 'updated_at', schema='etter')
    
    op.add_column('etter_master_company_role_job_track',
                  sa.Column('created_by', sa.String(length=255), nullable=True),
                  schema='etter')
    op.add_column('etter_master_company_role_job_track',
                  sa.Column('modified_by', sa.String(length=255), nullable=True),
                  schema='etter')
    op.add_column('etter_master_company_role_job_track',
                  sa.Column('created_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
                  schema='etter')
    op.add_column('etter_master_company_role_job_track',
                  sa.Column('modified_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
                  schema='etter')
    op.drop_column('etter_master_company_role_job_track', 'created_at', schema='etter')
    op.drop_column('etter_master_company_role_job_track', 'updated_at', schema='etter')
    
    op.add_column('etter_master_company_role_management_level',
                  sa.Column('created_by', sa.String(length=255), nullable=True),
                  schema='etter')
    op.add_column('etter_master_company_role_management_level',
                  sa.Column('modified_by', sa.String(length=255), nullable=True),
                  schema='etter')
    op.add_column('etter_master_company_role_management_level',
                  sa.Column('created_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
                  schema='etter')
    op.add_column('etter_master_company_role_management_level',
                  sa.Column('modified_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
                  schema='etter')
    op.drop_column('etter_master_company_role_management_level', 'created_at', schema='etter')
    op.drop_column('etter_master_company_role_management_level', 'updated_at', schema='etter')
    
    op.add_column('etter_master_skill_taxonomy_categories',
                  sa.Column('created_by', sa.String(length=255), nullable=True),
                  schema='etter')
    op.add_column('etter_master_skill_taxonomy_categories',
                  sa.Column('modified_by', sa.String(length=255), nullable=True),
                  schema='etter')
    op.add_column('etter_master_skill_taxonomy_categories',
                  sa.Column('created_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
                  schema='etter')
    op.add_column('etter_master_skill_taxonomy_categories',
                  sa.Column('modified_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
                  schema='etter')
    op.drop_column('etter_master_skill_taxonomy_categories', 'created_at', schema='etter')
    op.drop_column('etter_master_skill_taxonomy_categories', 'updated_at', schema='etter')
    
    op.create_table('etter_master_tech_stack_category',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=250), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=True),
    sa.Column('modified_by', sa.String(length=255), nullable=True),
    sa.Column('created_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    schema='etter'
    )
    
    op.create_table('etter_tech_stack_taxonomy',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('tech_stack_name', sa.String(length=250), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('image_link', sa.String(length=1000), nullable=True),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('tech_stack_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('approver_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=True),
    sa.Column('modified_by', sa.String(length=255), nullable=True),
    sa.Column('created_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['approver_id'], ['etter.etter_users.id'], ),
    sa.ForeignKeyConstraint(['category_id'], ['etter.etter_master_tech_stack_category.id'], ),
    sa.ForeignKeyConstraint(['company_id'], ['iris1.iris1_mastercompany.id'], ),
    sa.ForeignKeyConstraint(['tech_stack_id'], ['iris1.iris1_digitalapplicationsandplatform.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['etter.etter_users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('company_id', 'tech_stack_name', name='uix_tech_stack_taxonomy_company_tech_stack_name'),
    schema='etter'
    )


def downgrade() -> None:
    """Downgrade schema."""
    
    op.drop_table('etter_tech_stack_taxonomy', schema='etter')
    op.drop_table('etter_master_tech_stack_category', schema='etter')
    
    op.add_column('etter_master_skill_taxonomy_categories',
                  sa.Column('created_at', sa.DateTime(), nullable=False),
                  schema='etter')
    op.add_column('etter_master_skill_taxonomy_categories',
                  sa.Column('updated_at', sa.DateTime(), nullable=True),
                  schema='etter')
    op.drop_column('etter_master_skill_taxonomy_categories', 'modified_on', schema='etter')
    op.drop_column('etter_master_skill_taxonomy_categories', 'created_on', schema='etter')
    op.drop_column('etter_master_skill_taxonomy_categories', 'modified_by', schema='etter')
    op.drop_column('etter_master_skill_taxonomy_categories', 'created_by', schema='etter')
    
    op.add_column('etter_master_company_role_management_level',
                  sa.Column('created_at', sa.DateTime(), nullable=False),
                  schema='etter')
    op.add_column('etter_master_company_role_management_level',
                  sa.Column('updated_at', sa.DateTime(), nullable=True),
                  schema='etter')
    op.drop_column('etter_master_company_role_management_level', 'modified_on', schema='etter')
    op.drop_column('etter_master_company_role_management_level', 'created_on', schema='etter')
    op.drop_column('etter_master_company_role_management_level', 'modified_by', schema='etter')
    op.drop_column('etter_master_company_role_management_level', 'created_by', schema='etter')
    
    op.add_column('etter_master_company_role_job_track',
                  sa.Column('created_at', sa.DateTime(), nullable=False),
                  schema='etter')
    op.add_column('etter_master_company_role_job_track',
                  sa.Column('updated_at', sa.DateTime(), nullable=True),
                  schema='etter')
    op.drop_column('etter_master_company_role_job_track', 'modified_on', schema='etter')
    op.drop_column('etter_master_company_role_job_track', 'created_on', schema='etter')
    op.drop_column('etter_master_company_role_job_track', 'modified_by', schema='etter')
    op.drop_column('etter_master_company_role_job_track', 'created_by', schema='etter')
    
    op.add_column('etter_master_company_role_job_family',
                  sa.Column('created_at', sa.DateTime(), nullable=False),
                  schema='etter')
    op.add_column('etter_master_company_role_job_family',
                  sa.Column('updated_at', sa.DateTime(), nullable=True),
                  schema='etter')
    op.drop_column('etter_master_company_role_job_family', 'modified_on', schema='etter')
    op.drop_column('etter_master_company_role_job_family', 'created_on', schema='etter')
    op.drop_column('etter_master_company_role_job_family', 'modified_by', schema='etter')
    op.drop_column('etter_master_company_role_job_family', 'created_by', schema='etter')
    
    op.add_column('etter_master_company_role_occupation',
                  sa.Column('created_at', sa.DateTime(), nullable=False),
                  schema='etter')
    op.add_column('etter_master_company_role_occupation',
                  sa.Column('updated_at', sa.DateTime(), nullable=True),
                  schema='etter')
    op.drop_column('etter_master_company_role_occupation', 'modified_on', schema='etter')
    op.drop_column('etter_master_company_role_occupation', 'created_on', schema='etter')
    op.drop_column('etter_master_company_role_occupation', 'modified_by', schema='etter')
    op.drop_column('etter_master_company_role_occupation', 'created_by', schema='etter')
