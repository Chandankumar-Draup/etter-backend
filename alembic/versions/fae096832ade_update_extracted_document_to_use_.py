"""update_extracted_document_to_use_approver_model

Revision ID: fae096832ade
Revises: ebab3959204d
Create Date: 2026-01-22 14:14:42.891581

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'fae096832ade'
down_revision: Union[str, None] = 'ebab3959204d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str, schema: str = 'etter') -> bool:
    """Check if a column exists in a table."""
    connection = op.get_bind()
    inspector = inspect(connection)
    columns = [col['name'] for col in inspector.get_columns(table_name, schema=schema)]
    return column_name in columns


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('etter_extracted_document', sa.Column('approver_id', sa.Integer(), nullable=True), schema='etter')
    op.add_column('etter_extracted_document', sa.Column('approved_on', sa.DateTime(), nullable=True), schema='etter')
    op.add_column('etter_extracted_document', sa.Column('created_by', sa.String(length=255), nullable=True), schema='etter')
    op.add_column('etter_extracted_document', sa.Column('modified_by', sa.String(length=255), nullable=True), schema='etter')
    
    op.execute("ALTER TABLE etter.etter_extracted_document RENAME COLUMN created_at TO created_on")
    op.execute("ALTER TABLE etter.etter_extracted_document RENAME COLUMN updated_at TO modified_on")
    
    op.execute("""
        UPDATE etter.etter_extracted_document 
        SET modified_on = created_on 
        WHERE modified_on IS NULL
    """)
    
    op.alter_column('etter_extracted_document', 'modified_on', nullable=False, schema='etter')
    
    op.create_foreign_key(
        'etter_extracted_document_approver_id_fkey',
        'etter_extracted_document',
        'etter_users',
        ['approver_id'],
        ['id'],
        source_schema='etter',
        referent_schema='etter'
    )
    
    op.add_column('etter_role_taxonomy', sa.Column('approval_status', sa.String(length=50), nullable=True), schema='etter')
    if not column_exists('etter_role_taxonomy', 'approved_on'):
        op.add_column('etter_role_taxonomy', sa.Column('approved_on', sa.DateTime(), nullable=True), schema='etter')
    
    op.execute("""
        UPDATE etter.etter_role_taxonomy 
        SET approval_status = status
    """)
    
    op.alter_column('etter_role_taxonomy', 'approval_status', nullable=False, server_default='pending', schema='etter')
    op.drop_column('etter_role_taxonomy', 'status', schema='etter')
    
    op.add_column('etter_skill_taxonomy', sa.Column('approval_status', sa.String(length=50), nullable=True), schema='etter')
    if not column_exists('etter_skill_taxonomy', 'approved_on'):
        op.add_column('etter_skill_taxonomy', sa.Column('approved_on', sa.DateTime(), nullable=True), schema='etter')
    
    op.execute("""
        UPDATE etter.etter_skill_taxonomy 
        SET approval_status = status
    """)
    
    op.alter_column('etter_skill_taxonomy', 'approval_status', nullable=False, server_default='pending', schema='etter')
    op.drop_column('etter_skill_taxonomy', 'status', schema='etter')
    
    op.add_column('etter_tech_stack_taxonomy', sa.Column('approval_status', sa.String(length=50), nullable=True), schema='etter')
    if not column_exists('etter_tech_stack_taxonomy', 'approved_on'):
        op.add_column('etter_tech_stack_taxonomy', sa.Column('approved_on', sa.DateTime(), nullable=True), schema='etter')
    
    op.execute("""
        UPDATE etter.etter_tech_stack_taxonomy 
        SET approval_status = status
    """)
    
    op.alter_column('etter_tech_stack_taxonomy', 'approval_status', nullable=False, server_default='pending', schema='etter')
    op.drop_column('etter_tech_stack_taxonomy', 'status', schema='etter')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('etter_tech_stack_taxonomy', sa.Column('status', sa.VARCHAR(length=50), nullable=True), schema='etter')
    
    op.execute("""
        UPDATE etter.etter_tech_stack_taxonomy 
        SET status = approval_status
    """)
    
    op.alter_column('etter_tech_stack_taxonomy', 'status', nullable=False, server_default=sa.text("'pending'::character varying"), schema='etter')
    if column_exists('etter_tech_stack_taxonomy', 'approved_on'):
        op.drop_column('etter_tech_stack_taxonomy', 'approved_on', schema='etter')
    op.drop_column('etter_tech_stack_taxonomy', 'approval_status', schema='etter')
    
    op.add_column('etter_skill_taxonomy', sa.Column('status', sa.VARCHAR(length=50), nullable=True), schema='etter')
    
    op.execute("""
        UPDATE etter.etter_skill_taxonomy 
        SET status = approval_status
    """)
    
    op.alter_column('etter_skill_taxonomy', 'status', nullable=False, server_default=sa.text("'pending'::character varying"), schema='etter')
    if column_exists('etter_skill_taxonomy', 'approved_on'):
        op.drop_column('etter_skill_taxonomy', 'approved_on', schema='etter')
    op.drop_column('etter_skill_taxonomy', 'approval_status', schema='etter')
    
    op.add_column('etter_role_taxonomy', sa.Column('status', sa.VARCHAR(length=50), nullable=True), schema='etter')
    
    op.execute("""
        UPDATE etter.etter_role_taxonomy 
        SET status = approval_status
    """)
    
    op.alter_column('etter_role_taxonomy', 'status', nullable=False, server_default=sa.text("'pending'::character varying"), schema='etter')
    if column_exists('etter_role_taxonomy', 'approved_on'):
        op.drop_column('etter_role_taxonomy', 'approved_on', schema='etter')
    op.drop_column('etter_role_taxonomy', 'approval_status', schema='etter')
    
    op.drop_constraint('etter_extracted_document_approver_id_fkey', 'etter_extracted_document', schema='etter', type_='foreignkey')
    
    op.alter_column('etter_extracted_document', 'modified_on', nullable=True, schema='etter')
    
    op.execute("ALTER TABLE etter.etter_extracted_document RENAME COLUMN modified_on TO updated_at")
    op.execute("ALTER TABLE etter.etter_extracted_document RENAME COLUMN created_on TO created_at")
    
    op.drop_column('etter_extracted_document', 'modified_by', schema='etter')
    op.drop_column('etter_extracted_document', 'created_by', schema='etter')
    op.drop_column('etter_extracted_document', 'approved_on', schema='etter')
    op.drop_column('etter_extracted_document', 'approver_id', schema='etter')
