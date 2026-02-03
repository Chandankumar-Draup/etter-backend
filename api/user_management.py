import base64
import re
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from models.auth import User, GroupType
from models.etter import MasterCompany
from schemas.user_management_schemas import (
    UserListResponse, CreateUserRequest, CreateUserResponse, 
    UpdateUserRequest, UpdateCompanyImagesRequest, CompanyImagesResponse,
    GetUsersRequest, PaginatedUserResponse, SSODetails
)
from services.auth import verify_token, ResponseModel
from settings.database import get_db
from common.pagination import paginate
from services.email_service import email_service
from common.common_utils import getLoginLink
from typing import List, Optional
import secrets
import string


user_management_router = APIRouter(prefix="/admin", tags=["User Management"])


def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for _ in range(length))


def extract_name_from_email(email: str):
    email_part = email.split('@')[0]
    
    if '.' in email_part:
        parts = email_part.split('.')
        first_name = parts[0].capitalize()
        last_name = parts[1].capitalize() if len(parts) > 1 else ""
    elif '_' in email_part:
        parts = email_part.split('_')
        first_name = parts[0].capitalize()
        last_name = parts[1].capitalize() if len(parts) > 1 else ""
    else:
        first_name = email_part.capitalize()
        last_name = ""
    
    return first_name, last_name


# def generate_username_from_email(email: str, db: Session):
#     email_part = email.split('@')[0]
#     base_username = email_part.lower()
#     username = base_username
#
#     counter = 1
#     while db.query(User).filter(User.username == username).first():
#         username = f"{base_username}{counter}"
#         counter += 1
#
#     return username


@user_management_router.post("/users", response_model=PaginatedUserResponse)
async def get_all_users(
    request: GetUsersRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    draup_user_data = draup_user.data
    etter_user_obj = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if etter_user_obj.group not in [GroupType.ADMIN, GroupType.SUPER_ADMIN]:
        raise HTTPException(
            status_code=403, detail="Only admins can access user management"
        )

    query = db.query(User)

    if etter_user_obj.group == GroupType.SUPER_ADMIN:
        if request.company_name:
            company = (
                db.query(MasterCompany)
                .filter(MasterCompany.company_name == request.company_name)
                .first()
            )
            if company:
                query = query.filter(User.company_id == company.id)
            else:
                return PaginatedUserResponse(
                    users=[],
                    total_count=0,
                    page=request.page,
                    size=request.size,
                    total_pages=0,
                )
    else:
        query = query.filter(User.company_id == etter_user_obj.company_id)

    if request.email:
        query = query.filter(User.email.ilike(f"%{request.email.lower()}%"))

    query = query.order_by(User.id.desc())

    paginated_result = paginate(query, page=request.page, page_size=request.size)
    users = paginated_result.items

    user_list = []
    for user in users:
        company = (
            db.query(MasterCompany)
            .filter(MasterCompany.id == user.company_id)
            .first()
        )
        # sso_credentials = db.query(SSOCredentials).filter(SSOCredentials.company_id == user.company_id).first()
        #
        # sso_details = None
        # if sso_credentials:
        #     sso_details = SSODetails(
        #         client_id=sso_credentials.client_id,
        #         client_secret=sso_credentials.client_secret,
        #         redirect_uri=sso_credentials.redirect_uri,
        #         auth_uri=sso_credentials.auth_uri,
        #         token_uri=sso_credentials.token_uri,
        #         userinfo_uri=sso_credentials.userinfo_uri
        #     )

        user_list.append(
            UserListResponse(
                username=user.username,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                image=user.image,
                is_active=user.is_active,
                id=user.id,
                group=user.group,
                company_name=company.company_name if company else None,
                company_id=user.company_id,
                company_logo=company.logo if company else None,
                # sso_type=user.login_type if hasattr(user, "login_type") else None,
                # sso_details=sso_details
            )
        )

    return PaginatedUserResponse(
        users=user_list,
        total_count=paginated_result.total,
        page=paginated_result.page,
        size=paginated_result.page_size,
        total_pages=paginated_result.total_pages,
    )

#
# @user_management_router.post("/create-user", response_model=CreateUserResponse)
# async def create_user(
#     user_data: CreateUserRequest,
#     db: Session = Depends(get_db),
#     draup_user: ResponseModel = Depends(verify_token)
# ):
#     draup_user_data = draup_user.data
#     current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
#     login_link = getLoginLink()
#     if current_user.group not in [GroupType.ADMIN, GroupType.SUPER_ADMIN]:
#         raise HTTPException(status_code=403, detail="Only admins can create users")
#     if current_user.group == GroupType.SUPER_ADMIN:
#         if user_data.group not in [GroupType.RESEARCHER, GroupType.REVIEWER, GroupType.ADMIN, GroupType.SUPER_ADMIN]:
#             raise HTTPException(status_code=400, detail="Invalid group type")
#     else:
#         if user_data.group not in [GroupType.RESEARCHER, GroupType.REVIEWER, GroupType.ADMIN]:
#             raise HTTPException(status_code=400, detail="Regular admins can only create Researcher, Reviewer, or Admin users")
#
#     existing_user = db.query(User).filter(User.email == user_data.email).first()
#     if existing_user:
#         raise HTTPException(status_code=400, detail="User with this email already exists")
#
#     if current_user.group == GroupType.SUPER_ADMIN:
#         if not user_data.company_name:
#             raise HTTPException(status_code=400, detail="company_name is required for super admin")
#
#         company = db.query(MasterCompany).filter(MasterCompany.company_name == user_data.company_name).first()
#         if not company:
#             raise HTTPException(status_code=400, detail=f"Company with name '{user_data.company_name}' not found")
#
#         target_company_id = company.id
#     else:
#         target_company_id = current_user.company_id
#
#     first_name, last_name = extract_name_from_email(user_data.email)
#     username = generate_username_from_email(user_data.email, db)
#     password = generate_random_password()
#     # hashed_password = hash_password(password)
#
#     new_user = User(
#         email=user_data.email,
#         username=username,
#         company_id=target_company_id,
#         first_name=first_name,
#         last_name=last_name,
#         # password=hashed_password,
#         group=user_data.group,
#         is_active=True
#     )
#
#     db.add(new_user)
#     db.commit()
#     db.refresh(new_user)
#
#     email_sent = email_service.send_user_registration_email(
#         to_email=user_data.email,
#         username=username,
#         first_name=first_name,
#         last_name=last_name,
#         login_link=login_link
#     )
#
#     if not email_sent:
#         print(f"Warning: Failed to send registration email to {user_data.email}")
#
#     return CreateUserResponse(
#         id=new_user.id,
#         email=new_user.email,
#         user_id=new_user.user_id,
#         first_name=new_user.first_name,
#         last_name=new_user.last_name,
#         company_id=new_user.company_id,
#         group=new_user.group,
#         is_active=new_user.is_active
#     )


@user_management_router.put("/{user_id}", response_model=CreateUserResponse)
async def update_user(
    user_id: int,
    user_data: UpdateUserRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    draup_user_data = draup_user.data
    etter_user_obj = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if etter_user_obj.group not in [GroupType.ADMIN, GroupType.SUPER_ADMIN]:
        raise HTTPException(
            status_code=403, detail="Only admins can update users"
        )
    
    if etter_user_obj.group == GroupType.SUPER_ADMIN:
        user = db.query(User).filter(User.id == user_id).first()
    else:
        user = db.query(User).filter(User.id == user_id, User.company_id == etter_user_obj.company_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_data.group is not None:
        if etter_user_obj.group == GroupType.SUPER_ADMIN:
            if user_data.group not in [GroupType.RESEARCHER, GroupType.REVIEWER, GroupType.ADMIN, GroupType.SUPER_ADMIN]:
                raise HTTPException(status_code=400, detail="Invalid group type")
        else:
            if user_data.group not in [GroupType.RESEARCHER, GroupType.REVIEWER, GroupType.ADMIN]:
                raise HTTPException(status_code=400, detail="Regular admins can only assign Researcher, Reviewer, or Admin roles")
        user.group = user_data.group
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    if etter_user_obj.group == GroupType.SUPER_ADMIN and user_data.company_name:
        company = db.query(MasterCompany).filter(MasterCompany.company_name == user_data.company_name).first()
        if not company:
            raise HTTPException(status_code=400, detail=f"Company with name '{user_data.company_name}' not found")
        user.company_id = company.id
    
    # if user_data.sso_details:
        # existing_sso = db.query(SSOCredentials).filter(SSOCredentials.company_id == user.company_id).first()
        # if existing_sso:
        #     existing_sso.client_id = user_data.sso_details.client_id
        #     existing_sso.client_secret = user_data.sso_details.client_secret
        #     existing_sso.redirect_uri = user_data.sso_details.redirect_uri
        #     existing_sso.auth_uri = user_data.sso_details.auth_uri
        #     existing_sso.token_uri = user_data.sso_details.token_uri
        #     existing_sso.userinfo_uri = user_data.sso_details.userinfo_uri
        # else:
        #     new_sso = SSOCredentials(
        #         company_id=user.company_id,
        #         client_id=user_data.sso_details.client_id,
        #         client_secret=user_data.sso_details.client_secret,
        #         redirect_uri=user_data.sso_details.redirect_uri,
        #         auth_uri=user_data.sso_details.auth_uri,
        #         token_uri=user_data.sso_details.token_uri,
        #         userinfo_uri=user_data.sso_details.userinfo_uri
        #     )
        #     db.add(new_sso)
    
    db.commit()
    db.refresh(user)
    
    return CreateUserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        company_id=user.company_id,
        group=user.group,
        is_active=user.is_active
    )


@user_management_router.post("/company/images", response_model=CompanyImagesResponse)
async def update_company_images(
    light_theme_image: Optional[UploadFile] = File(None),
    dark_theme_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if current_user.group != GroupType.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can update company images")
    
    company = db.query(MasterCompany).filter(MasterCompany.id == current_user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if light_theme_image:
        image_content = await light_theme_image.read()
        base64_image = base64.b64encode(image_content).decode('utf-8')
        company.light_theme_image = f"data:{light_theme_image.content_type};base64,{base64_image}"
    
    if dark_theme_image:
        image_content = await dark_theme_image.read()
        base64_image = base64.b64encode(image_content).decode('utf-8')
        company.dark_theme_image = f"data:{dark_theme_image.content_type};base64,{base64_image}"
    
    db.commit()
    db.refresh(company)
    
    return CompanyImagesResponse(
        light_theme_image=company.light_theme_image,
        dark_theme_image=company.dark_theme_image
    )
