"""dafault users

Revision ID: f963f84b2779
Revises: dc7de4a97ce7
Create Date: 2025-08-18 14:22:11.229745

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f963f84b2779'
down_revision: Union[str, None] = 'dc7de4a97ce7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    connection = op.get_bind()
    
    op.alter_column('etter_users', 'company_id',
                    existing_type=sa.Integer(),
                    nullable=True,
                    schema='etter')
    
    default_users = [
        {
            "id": 9,
            "email": "chandankumar@draup.com",
            "username": "chandankumar",
            "company_name": "Draup",
            "first_name": "chandan",
            "last_name": "kumar",
            "password": "gsgdAGFS1452$%^FD",
            "group": "Researcher",
            "image": "",
            "is_active": True,
            "theme_config": '{"theme": "light", "isSystemTheme": false}',
            "login_type": "otp"
        },
        {
            "id": 4,
            "email": "rahul.kondi@draup.com",
            "username": "Rahul",
            "company_name": "Draup",
            "first_name": "Rahul",
            "last_name": "Kondi",
            "password": "3ATEDae12DS$%^FD",
            "group": "Super Admin",
            "image": "",
            "is_active": True,
            "theme_config": "{}",
            "login_type": "otp"
        },
        {
            "id": 11,
            "email": "sai.rahul@draup.com",
            "username": "sairahul",
            "company_name": "Draup",
            "first_name": "sai ",
            "last_name": "rahul",
            "password": "dhbdw!253@3!uSAH",
            "group": "Super Admin",
            "image": "",
            "is_active": True,
            "theme_config": '{"theme": "dark", "isSystemTheme": false}',
            "login_type": "otp"
        },
        {
            "id": 12,
            "email": "demo@draup.com",
            "username": "draupdemo",
            "company_name": "Draup",
            "first_name": "draup",
            "last_name": "demo",
            "password": "kbfw32@#$!35123r2",
            "group": "Researcher",
            "image": "",
            "is_active": True,
            "theme_config": '{"theme": "dark", "isSystemTheme": false}',
            "login_type": "otp"
        }
    ]
    
    for user in default_users:
        check_query = sa.text("SELECT id FROM etter.etter_users WHERE email = :email OR username = :username")
        result = connection.execute(check_query, {"email": user["email"], "username": user["username"]})
        
        if not result.fetchone():
            company_name = user.pop("company_name")
            company_id = None
            
            if company_name:
                company_query = sa.text("SELECT id FROM iris1.iris1_mastercompany WHERE company_name = :company_name")
                company_result = connection.execute(company_query, {"company_name": company_name})
                company_row = company_result.fetchone()
                if company_row:
                    company_id = company_row[0]
            
            user["company_id"] = company_id
            
            insert_query = sa.text("""
                INSERT INTO etter.etter_users
                (id, email, username, company_id, first_name, last_name, password, "group", image, is_active, theme_config, login_type)
                VALUES (:id, :email, :username, :company_id, :first_name, :last_name, :password, :group, :image, :is_active, :theme_config, :login_type)
            """)
            connection.execute(insert_query, user)
 
 
def downgrade() -> None:
    """Downgrade schema."""
    connection = op.get_bind()
    
    emails_to_remove = [
        "chandankumar@draup.com",
        "rahul.kondi@draup.com",
        "sai.rahul@draup.com",
        "demo@draup.com"
    ]
    
    for email in emails_to_remove:
        delete_query = sa.text("DELETE FROM etter.etter_users WHERE email = :email")
        connection.execute(delete_query, {"email": email})
    
    op.alter_column('etter_users', 'company_id',
                    existing_type=sa.Integer(),
                    nullable=False,
                    schema='etter')
