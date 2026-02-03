"""add_performance_indexes

Revision ID: 4032c657b281
Revises: a1b2c3d4e5f6
Create Date: 2025-12-29 13:00:01.644731

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4032c657b281'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('idx_etter_users_email', 'etter_users', ['email'], schema='etter')
    op.create_index('idx_etter_users_company_id', 'etter_users', ['company_id'], schema='etter')
    op.create_index('idx_etter_users_username', 'etter_users', ['username'], schema='etter')
    
    op.create_index('idx_etter_userworkflowshistory_user_id', 'etter_userworkflowshistory', ['user_id'], schema='etter')
    op.create_index('idx_etter_userworkflowshistory_workflow_id', 'etter_userworkflowshistory', ['workflow_id'], schema='etter')
    op.create_index('idx_etter_userworkflowshistory_status', 'etter_userworkflowshistory', ['workflow_status'], schema='etter')
    op.create_index(
        'idx_etter_userworkflowshistory_composite',
        'etter_userworkflowshistory',
        ['user_id', 'workflow_id', 'workflow_status'],
        schema='etter'
    )
    
    op.create_index('idx_s3_documents_tenant_id', 's3_documents', ['tenant_id'], schema='etter')
    op.create_index('idx_s3_documents_status', 's3_documents', ['status'], schema='etter')
    op.create_index('idx_s3_documents_created_at', 's3_documents', ['created_at'], schema='etter')
    op.create_index('idx_s3_documents_tenant_status', 's3_documents', ['tenant_id', 'status'], schema='etter')
    
    op.create_index('idx_chro_dashboard_workflow_id', 'chro_dashboard', ['workflow_id'], schema='etter')
    
    op.create_index('idx_iris1_mastercompany_company_name', 'iris1_mastercompany', ['company_name'], schema='iris1')


def downgrade() -> None:
    op.drop_index('idx_etter_users_email', schema='etter')
    op.drop_index('idx_etter_users_company_id', schema='etter')
    op.drop_index('idx_etter_users_username', schema='etter')
    
    op.drop_index('idx_etter_userworkflowshistory_user_id', schema='etter')
    op.drop_index('idx_etter_userworkflowshistory_workflow_id', schema='etter')
    op.drop_index('idx_etter_userworkflowshistory_status', schema='etter')
    op.drop_index('idx_etter_userworkflowshistory_composite', schema='etter')
    
    op.drop_index('idx_s3_documents_tenant_id', schema='etter')
    op.drop_index('idx_s3_documents_status', schema='etter')
    op.drop_index('idx_s3_documents_created_at', schema='etter')
    op.drop_index('idx_s3_documents_tenant_status', schema='etter')
    
    op.drop_index('idx_chro_dashboard_workflow_id', schema='etter')
    
    op.drop_index('idx_iris1_mastercompany_company_name', schema='iris1')
