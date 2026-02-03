"""fix_sso_otp_migration

Revision ID: e217ec738b3d
Revises: f5c517c3d0b5
Create Date: 2025-08-05 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e217ec738b3d'
down_revision: Union[str, None] = 'f5c517c3d0b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE TYPE login_type AS ENUM ('otp', 'sso')")
    
    op.add_column('etter_users',
                  sa.Column('login_type', sa.Enum('otp', 'sso', name='login_type'), nullable=False, server_default='otp'),
                  schema='etter')
    
    op.create_table('user_otp',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('otp', sa.String(length=6), nullable=False),
                    sa.Column('is_sent', sa.Boolean(), nullable=False, server_default='false'),
                    sa.Column('valid_till', sa.DateTime(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
                    sa.ForeignKeyConstraint(['user_id'], ['etter.etter_users.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema='etter')
    
    op.create_table('sso_credentials',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('company_id', sa.Integer(), nullable=False),
                    sa.Column('client_id', sa.String(length=255), nullable=False),
                    sa.Column('client_secret', sa.String(length=500), nullable=False),
                    sa.Column('redirect_uri', sa.String(length=500), nullable=False),
                    sa.Column('auth_uri', sa.String(length=500), nullable=False),
                    sa.Column('token_uri', sa.String(length=500), nullable=False),
                    sa.Column('userinfo_uri', sa.String(length=500), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
                    sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
                    sa.ForeignKeyConstraint(['company_id'], ['iris1.iris1_mastercompany.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema='etter')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('sso_credentials', schema='etter')
    op.drop_table('user_otp', schema='etter')
    op.drop_column('etter_users', 'login_type', schema='etter')
    op.execute("DROP TYPE login_type")
