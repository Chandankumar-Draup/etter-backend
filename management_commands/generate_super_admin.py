#!/usr/bin/env python3

import click
import sys
import os


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@click.command()
@click.argument('emails')
def generate_super_admin(emails):
    from sqlalchemy.orm import Session
    from settings.database import get_db
    from models.auth import User, GroupType
    from models.etter import MasterCompany
    from services.auth import hash_password
    import secrets
    import string
    
    def generate_random_password(length=12):
        characters = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    def extract_name_from_email(email: str):
        try:
            username = email.split('@')[0]
            if '.' in username:
                first_name, last_name = username.split('.', 1)
                first_name = first_name.capitalize()
                last_name = last_name.capitalize()
            else:
                first_name = username.capitalize()
                last_name = "User"
            return first_name, last_name
        except:
            return "User", "Default"
    
    def generate_username_from_email(email: str, db: Session):
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1
        
        return username
    
    def get_or_create_draup_company(db: Session):
        company = db.query(MasterCompany).filter(
            MasterCompany.company_name == 'Draup Inc.'
        ).first()
        
        if company:
            print(f"✅ Found existing company: {company.company_name} (ID: {company.id})")
            return company
        

        company = db.query(MasterCompany).first()
        if company:
            print(f"✅ Using existing company: {company.company_name} (ID: {company.id})")
            return company
        

        raise Exception("No companies found in database")
    
    def create_super_admin_from_email(email: str, db: Session, company_id: int):
        email = email.strip()
        
        if not email:
            print(f"⚠️  Skipping empty email")
            return None, "skipped"
        

        existing_user = db.query(User).filter(User.email == email).first()
        
        if existing_user:
            if existing_user.group == GroupType.SUPER_ADMIN:
                print(f"✅ User {email} is already a SUPER_ADMIN")
                return existing_user, "already_admin"
            else:
                print(f"🔄 Updating existing user {email} to SUPER_ADMIN")
                existing_user.group = GroupType.SUPER_ADMIN
                existing_user.company_id = company_id
                db.commit()
                db.refresh(existing_user)
                return existing_user, "updated"
        

        first_name, last_name = extract_name_from_email(email)
        username = generate_username_from_email(email, db)
        # password = generate_random_password()
        # hashed_password = hash_password(password)
        
        new_user = User(
            email=email,
            username=username,
            company_id=company_id,
            first_name=first_name,
            last_name=last_name,
            # password=hashed_password,
            group=GroupType.SUPER_ADMIN,
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"✅ Created SUPER_ADMIN: {email}")
        print(f"   Username: {username}")
        # print(f"   Password: {password}")
        print(f"   Name: {first_name} {last_name}")
        print(f"   Company: Draup Inc.")
        
        return new_user, "created"
    

    email_list = [email.strip() for email in emails.split(';') if email.strip()]
    
    if not email_list:
        print("❌ No valid email addresses provided")
        return
    
    print(f"🎯 Processing {len(email_list)} email(s):")
    for email in email_list:
        print(f"   - {email}")
    print()
    
    db = next(get_db())
    
    try:

        company = get_or_create_draup_company(db)
        print()
        

        created_users = []
        updated_users = []
        skipped_users = []
        
        for email in email_list:
            try:
                result, action = create_super_admin_from_email(email, db, company.id)
                if result:
                    if action == "created":
                        created_users.append(email)
                    elif action == "updated":
                        updated_users.append(email)
                    elif action == "already_admin":
                        skipped_users.append(email)
                    else:
                        skipped_users.append(email)
                else:
                    skipped_users.append(email)
                print()
            except Exception as e:
                print(f"❌ Error processing {email}: {str(e)}")
                skipped_users.append(email)
                print()
        

        print("📊 SUMMARY:")
        print(f"   ✅ Created: {len(created_users)} user(s)")
        print(f"   🔄 Updated: {len(updated_users)} user(s)")
        print(f"   ⚠️  Skipped: {len(skipped_users)} user(s)")
        
        if created_users:
            print(f"\n🆕 New SUPER_ADMIN users created:")
            for email in created_users:
                print(f"   - {email}")
        
        if updated_users:
            print(f"\n🔄 Users updated to SUPER_ADMIN:")
            for email in updated_users:
                print(f"   - {email}")
        
        if skipped_users:
            print(f"\n⚠️  Skipped emails:")
            for email in skipped_users:
                print(f"   - {email}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    generate_super_admin()
