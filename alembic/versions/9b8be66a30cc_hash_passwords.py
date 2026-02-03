"""hash passwords

Revision ID: 9b8be66a30cc
Revises: f963f84b2779
Create Date: 2025-08-20 15:15:02.172355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import bcrypt
import re


# revision identifiers, used by Alembic.
revision: str = '9b8be66a30cc'
down_revision: Union[str, None] = 'f963f84b2779'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def is_already_hashed(password: str) -> bool:
    """Check if password is already bcrypt hashed"""
    if not password:
        return False
    
    bcrypt_pattern = re.compile(r'^\$2[aby]\$\d{1,2}\$[./A-Za-z0-9]{53}$')
    return bool(bcrypt_pattern.match(password))


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def upgrade() -> None:
    """Upgrade schema."""
    connection = op.get_bind()
    
    users_to_hash = [
        {
            "email": "chandankumar@draup.com",
            "plain_password": "gsgdAGFS1452$%^FD"
        },
        {
            "email": "rahul.kondi@draup.com", 
            "plain_password": "3ATEDae12DS$%^FD"
        },
        {
            "email": "sai.rahul@draup.com",
            "plain_password": "dhbdw!253@3!uSAH"
        },
        {
            "email": "demo@draup.com",
            "plain_password": "kbfw32@#$!35123r2"
        }
    ]
    
    for user_data in users_to_hash:
        email = user_data["email"]
        plain_password = user_data["plain_password"]
        
        select_query = sa.text("SELECT password FROM etter.etter_users WHERE email = :email")
        result = connection.execute(select_query, {"email": email})
        user_row = result.fetchone()
        
        if user_row:
            current_password = user_row[0]
            
            if is_already_hashed(current_password):
                print(f"Password for {email} is already hashed, skipping...")
                continue
            
            hashed_password = hash_password(plain_password)
            
            update_query = sa.text("""
                UPDATE etter.etter_users 
                SET password = :hashed_password 
                WHERE email = :email
            """)
            
            connection.execute(update_query, {
                "hashed_password": hashed_password,
                "email": email
            })
            print(f"Successfully hashed password for {email}")


def downgrade() -> None:
    """Downgrade schema."""
    connection = op.get_bind()
    
    users_to_revert = [
        {
            "email": "chandankumar@draup.com",
            "plain_password": "gsgdAGFS1452$%^FD"
        },
        {
            "email": "rahul.kondi@draup.com", 
            "plain_password": "3ATEDae12DS$%^FD"
        },
        {
            "email": "sai.rahul@draup.com",
            "plain_password": "dhbdw!253@3!uSAH"
        },
        {
            "email": "demo@draup.com",
            "plain_password": "kbfw32@#$!35123r2"
        }
    ]
    
    for user_data in users_to_revert:
        email = user_data["email"]
        plain_password = user_data["plain_password"]
        
        update_query = sa.text("""
            UPDATE etter.etter_users 
            SET password = :plain_password 
            WHERE email = :email
        """)
        
        connection.execute(update_query, {
            "plain_password": plain_password,
            "email": email
        })
