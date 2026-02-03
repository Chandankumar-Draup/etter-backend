"""add_extraction_session_and_document_tables

Revision ID: e9f1a2b3c4d5
Revises: 20251128_153910_add_filesystem_mode
Create Date: 2025-12-08 16:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e9f1a2b3c4d5'
down_revision: Union[str, None] = '20251128_153910'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create extraction session and document tables."""
    
    # Create enum types
    op.execute("""
        CREATE TYPE etter.extraction_session_status AS ENUM ('ACTIVE', 'COMPLETED', 'ARCHIVED')
    """)
    op.execute("""
        CREATE TYPE etter.extraction_status AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')
    """)
    op.execute("""
        CREATE TYPE etter.approval_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED')
    """)
    
    # Create extraction session table
    op.create_table(
        'etter_extraction_session',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('ACTIVE', 'COMPLETED', 'ARCHIVED', name='extraction_session_status', schema='etter', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['etter.etter_users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='etter'
    )
    op.create_index(
        'ix_etter_extraction_session_user_id',
        'etter_extraction_session',
        ['user_id'],
        unique=False,
        schema='etter'
    )
    op.create_index(
        'ix_etter_extraction_session_status',
        'etter_extraction_session',
        ['status'],
        unique=False,
        schema='etter'
    )
    
    # Create extracted document table
    op.create_table(
        'etter_extracted_document',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('document_name', sa.String(500), nullable=True),
        sa.Column('status', postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='extraction_status', schema='etter', create_type=False), nullable=False),
        sa.Column('error_message', sa.String(1000), nullable=True),
        sa.Column('document_type', sa.String(50), nullable=True),
        sa.Column('extraction_confidence', sa.Integer(), nullable=True),
        sa.Column('extraction_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tasks', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('skills', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('stages', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('task_to_skill', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('approval_status', postgresql.ENUM('PENDING', 'APPROVED', 'REJECTED', name='approval_status', schema='etter', create_type=False), nullable=False),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['etter.etter_extraction_session.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approved_by'], ['etter.etter_users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='etter'
    )
    op.create_index(
        'ix_etter_extracted_document_session_id',
        'etter_extracted_document',
        ['session_id'],
        unique=False,
        schema='etter'
    )
    op.create_index(
        'ix_etter_extracted_document_document_id',
        'etter_extracted_document',
        ['document_id'],
        unique=False,
        schema='etter'
    )
    op.create_index(
        'ix_etter_extracted_document_status',
        'etter_extracted_document',
        ['status'],
        unique=False,
        schema='etter'
    )
    op.create_index(
        'ix_etter_extracted_document_approval_status',
        'etter_extracted_document',
        ['approval_status'],
        unique=False,
        schema='etter'
    )


def downgrade() -> None:
    """Drop extraction session and document tables."""
    op.drop_index('ix_etter_extracted_document_approval_status', table_name='etter_extracted_document', schema='etter')
    op.drop_index('ix_etter_extracted_document_status', table_name='etter_extracted_document', schema='etter')
    op.drop_index('ix_etter_extracted_document_document_id', table_name='etter_extracted_document', schema='etter')
    op.drop_index('ix_etter_extracted_document_session_id', table_name='etter_extracted_document', schema='etter')
    op.drop_table('etter_extracted_document', schema='etter')
    
    op.drop_index('ix_etter_extraction_session_status', table_name='etter_extraction_session', schema='etter')
    op.drop_index('ix_etter_extraction_session_user_id', table_name='etter_extraction_session', schema='etter')
    op.drop_table('etter_extraction_session', schema='etter')
    
    # Drop enum types
    op.execute("DROP TYPE etter.approval_status")
    op.execute("DROP TYPE etter.extraction_status")
    op.execute("DROP TYPE etter.extraction_session_status")
