"""change in_demand to boolean

Revision ID: dd3e7d39a9aa
Revises: 556c20c0eadd
Create Date: 2025-12-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'dd3e7d39a9aa'
down_revision: Union[str, None] = '556c20c0eadd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE etter.etter_skill_taxonomy 
        ALTER COLUMN in_demand DROP DEFAULT
    """)
    
    op.execute("""
        ALTER TABLE etter.etter_skill_taxonomy 
        ALTER COLUMN in_demand TYPE boolean 
        USING CASE 
            WHEN in_demand::text = 'true' OR in_demand::text = 'True' OR in_demand::text = '1' THEN true
            ELSE false
        END
    """)
    
    op.execute("""
        ALTER TABLE etter.etter_skill_taxonomy 
        ALTER COLUMN in_demand SET DEFAULT false
    """)
    
    op.execute("""
        ALTER TABLE etter.etter_skill_taxonomy 
        ALTER COLUMN in_demand SET NOT NULL
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE etter.etter_skill_taxonomy 
        ALTER COLUMN in_demand DROP DEFAULT
    """)
    
    op.execute("""
        ALTER TABLE etter.etter_skill_taxonomy 
        ALTER COLUMN in_demand TYPE varchar(50) 
        USING CASE 
            WHEN in_demand = true THEN 'true'
            ELSE 'false'
        END
    """)
    
    op.execute("""
        ALTER TABLE etter.etter_skill_taxonomy 
        ALTER COLUMN in_demand DROP NOT NULL
    """)
    
    op.execute("""
        ALTER TABLE etter.etter_skill_taxonomy 
        ALTER COLUMN in_demand SET DEFAULT 'false'
    """)
