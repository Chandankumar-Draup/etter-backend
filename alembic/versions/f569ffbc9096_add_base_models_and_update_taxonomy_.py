"""add_base_models_and_update_taxonomy_tables

Revision ID: f569ffbc9096
Revises: 374139242bfc
Create Date: 2026-01-13 11:58:54.282622

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f569ffbc9096'
down_revision: Union[str, None] = '374139242bfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    connection = op.get_bind()
    
    op.add_column('etter_role_taxonomy', 
                  sa.Column('created_by', sa.String(length=255), nullable=True),
                  schema='etter')
    
    op.add_column('etter_role_taxonomy',
                  sa.Column('modified_by_new', sa.String(length=255), nullable=True),
                  schema='etter')
    
    update_query = sa.text("""
        UPDATE etter.etter_role_taxonomy rt
        SET modified_by_new = u.username
        FROM etter.etter_users u
        WHERE rt.modified_by = u.id
    """)
    connection.execute(update_query)
    
    op.drop_constraint('fk_role_taxonomy_modified_by', 'etter_role_taxonomy', schema='etter', type_='foreignkey')
    op.drop_column('etter_role_taxonomy', 'modified_by', schema='etter')
    op.alter_column('etter_role_taxonomy', 'modified_by_new',
                   new_column_name='modified_by',
                   schema='etter')
    
    op.alter_column('etter_role_taxonomy', 'updated_on',
                   new_column_name='modified_on',
                   existing_type=sa.DateTime(),
                   existing_nullable=True,
                   schema='etter')
    
    op.add_column('etter_skill_taxonomy',
                  sa.Column('created_by', sa.String(length=255), nullable=True),
                  schema='etter')
    
    op.add_column('etter_skill_taxonomy',
                  sa.Column('modified_by_new', sa.String(length=255), nullable=True),
                  schema='etter')
    
    update_query_skill = sa.text("""
        UPDATE etter.etter_skill_taxonomy st
        SET modified_by_new = u.username
        FROM etter.etter_users u
        WHERE st.modified_by = u.id
    """)
    connection.execute(update_query_skill)
    
    op.drop_constraint('fk_skill_taxonomy_modified_by', 'etter_skill_taxonomy', schema='etter', type_='foreignkey')
    op.drop_column('etter_skill_taxonomy', 'modified_by', schema='etter')
    op.alter_column('etter_skill_taxonomy', 'modified_by_new',
                   new_column_name='modified_by',
                   schema='etter')
    
    op.drop_column('etter_skill_taxonomy', 'updated_on', schema='etter')


def downgrade() -> None:
    """Downgrade schema."""
    connection = op.get_bind()
    
    op.add_column('etter_skill_taxonomy',
                  sa.Column('updated_on', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
                  schema='etter')
    
    op.add_column('etter_skill_taxonomy',
                  sa.Column('modified_by_id', sa.Integer(), nullable=True),
                  schema='etter')
    
    update_query_skill = sa.text("""
        UPDATE etter.etter_skill_taxonomy st
        SET modified_by_id = u.id
        FROM etter.etter_users u
        WHERE st.modified_by = u.username
    """)
    connection.execute(update_query_skill)
    
    op.drop_column('etter_skill_taxonomy', 'modified_by', schema='etter')
    op.alter_column('etter_skill_taxonomy', 'modified_by_id',
                   new_column_name='modified_by',
                   schema='etter')
    op.create_foreign_key('fk_skill_taxonomy_modified_by', 'etter_skill_taxonomy', 'etter_users',
                         ['modified_by'], ['id'], source_schema='etter', referent_schema='etter')
    
    op.drop_column('etter_skill_taxonomy', 'created_by', schema='etter')
    
    op.alter_column('etter_role_taxonomy', 'modified_on',
                   new_column_name='updated_on',
                   existing_type=sa.DateTime(),
                   existing_nullable=True,
                   schema='etter')
    
    op.add_column('etter_role_taxonomy',
                  sa.Column('modified_by_id', sa.Integer(), nullable=True),
                  schema='etter')
    
    update_query = sa.text("""
        UPDATE etter.etter_role_taxonomy rt
        SET modified_by_id = u.id
        FROM etter.etter_users u
        WHERE rt.modified_by = u.username
    """)
    connection.execute(update_query)
    
    op.drop_column('etter_role_taxonomy', 'modified_by', schema='etter')
    op.alter_column('etter_role_taxonomy', 'modified_by_id',
                   new_column_name='modified_by',
                   schema='etter')
    op.create_foreign_key('fk_role_taxonomy_modified_by', 'etter_role_taxonomy', 'etter_users',
                         ['modified_by'], ['id'], source_schema='etter', referent_schema='etter')
    
    op.drop_column('etter_role_taxonomy', 'created_by', schema='etter')
