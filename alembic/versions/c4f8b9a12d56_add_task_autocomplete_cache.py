"""add task autocomplete cache

Revision ID: c4f8b9a12d56
Revises: ab228f2269cf
Create Date: 2025-11-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c4f8b9a12d56'
down_revision: Union[str, None] = 'ab228f2269cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable pg_trgm extension for GIN indexes (if not already enabled)
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    # Create task autocomplete cache table
    op.create_table('etter_task_autocomplete_cache',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_name', sa.String(length=500), nullable=False),
        sa.Column('company', sa.String(length=200), nullable=False),
        sa.Column('role', sa.String(length=200), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_name', 'company', 'role', name='uix_task_company_role'),
        schema='etter'
    )

    # Create GIN index for fast prefix matching on task_name
    op.execute("""
        CREATE INDEX idx_task_name_prefix
        ON etter.etter_task_autocomplete_cache
        USING gin(task_name gin_trgm_ops)
    """)

    # Create B-tree index for company+role filtering (most common query pattern)
    op.create_index(
        'idx_company_role',
        'etter_task_autocomplete_cache',
        ['company', 'role'],
        schema='etter'
    )

    # Create index on company only (for future company-only queries)
    op.create_index(
        'idx_company',
        'etter_task_autocomplete_cache',
        ['company'],
        schema='etter'
    )

    # Create index on updated_at for TTL checks and cache staleness
    op.create_index(
        'idx_updated_at',
        'etter_task_autocomplete_cache',
        ['updated_at'],
        schema='etter'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index('idx_updated_at', table_name='etter_task_autocomplete_cache', schema='etter')
    op.drop_index('idx_company', table_name='etter_task_autocomplete_cache', schema='etter')
    op.drop_index('idx_company_role', table_name='etter_task_autocomplete_cache', schema='etter')
    op.execute('DROP INDEX IF EXISTS etter.idx_task_name_prefix')

    # Drop table
    op.drop_table('etter_task_autocomplete_cache', schema='etter')

    # Note: Not dropping pg_trgm extension as it might be used by other tables
