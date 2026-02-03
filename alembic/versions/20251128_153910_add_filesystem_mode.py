"""add_filesystem_mode

Revision ID: 20251128_153910
Revises: 912854fa4a56
Create Date: 2025-11-28 15:39:10.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251128_153910'
down_revision: Union[str, None] = '912854fa4a56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add filesystem mode support."""
    # Add upload_mode enum
    upload_mode_enum = sa.Enum('FILESYSTEM', 'ROLE_BASED', name='uploadmode_v2')
    upload_mode_enum.create(op.get_bind())

    # Add columns
    op.add_column('s3_documents',
        sa.Column('upload_mode', upload_mode_enum, nullable=True),
        schema='etter'
    )
    op.add_column('s3_documents',
        sa.Column('folder_path', sa.Text(), nullable=True),
        schema='etter'
    )

    # Set existing records to ROLE_BASED (if any remain)
    op.execute("UPDATE etter.s3_documents SET upload_mode = 'ROLE_BASED'")

    # Make upload_mode non-nullable
    op.alter_column('s3_documents', 'upload_mode', nullable=False, schema='etter')

    # Add indexes
    op.create_index('ix_s3_documents_mode_folder', 's3_documents',
        ['upload_mode', 'folder_path', 'tenant_id'], schema='etter')

    # Add unique constraint for filesystem mode
    op.execute("""
        CREATE UNIQUE INDEX uq_s3_filesystem_path
        ON etter.s3_documents(tenant_id, folder_path, original_filename)
        WHERE upload_mode = 'FILESYSTEM' AND status != 'DELETED'
    """)

    # Migrate existing keys to include environment prefix (assumes QA environment)
    # This makes existing files accessible with new path structure
    op.execute("""
        UPDATE etter.s3_documents
        SET key = 'qa/' || key
        WHERE key NOT LIKE 'dev/%'
          AND key NOT LIKE 'qa/%'
          AND key NOT LIKE 'prod/%'
    """)


def downgrade() -> None:
    """Downgrade schema to remove filesystem mode support."""
    # Drop unique index
    op.execute("DROP INDEX IF EXISTS etter.uq_s3_filesystem_path")

    # Drop indexes
    op.drop_index('ix_s3_documents_mode_folder', table_name='s3_documents', schema='etter')

    # Drop columns
    op.drop_column('s3_documents', 'folder_path', schema='etter')
    op.drop_column('s3_documents', 'upload_mode', schema='etter')

    # Drop enum
    op.execute("DROP TYPE IF EXISTS uploadmode_v2")
