"""Add company_instance_name to s3_documents

Revision ID: 20251210_143500
Revises: 374139242bfc
Create Date: 2025-12-10 14:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251210_143500'
down_revision: Union[str, None] = '374139242bfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add company_instance_name column to s3_documents table
    op.add_column(
        's3_documents',
        sa.Column('company_instance_name', sa.Text(), nullable=True),
        schema='etter'
    )


def downgrade() -> None:
    # Remove company_instance_name column from s3_documents table
    op.drop_column('s3_documents', 'company_instance_name', schema='etter')
