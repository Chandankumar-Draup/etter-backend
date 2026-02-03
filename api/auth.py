import json
from common.logger import logger
from fastapi import APIRouter, HTTPException, Depends, Request, Header, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from schemas.auth_schemas import UserResponse, CreateToken, Token
from sqlalchemy import or_
from sqlalchemy.orm import Session
from models.auth import User
from services.auth import verify_token
import os
import base64
from services.auth import create_user, create_jwt_token, decode_jwt
from models.etter import MasterCompany
from settings.database import get_db
from io import BytesIO
from common.s3_utils import upload_to_s3_with_config, get_s3_environment
from api.s3.config import s3_config

from datetime import timedelta
from typing import Optional, List, Union
from pydantic import EmailStr


auth_router = APIRouter(prefix="/auth", tags=["Etter"])
from services.auth import ResponseModel

@auth_router.post('/get_token')
async def get_token(request: CreateToken):
    resp_dict = {"status": "success", "token": None, "error": None}
    try:
        username = request.username
        data = {"username": username}
        resp_dict["token"] = create_jwt_token(data, timedelta(minutes=5))
    except Exception as e:
        resp_dict["status"] = "failure"
        resp_dict["error"] = str(e)

    return resp_dict


@auth_router.post('/verify_workato_token')
async def verify_workato_token(request: Token, db: Session = Depends(get_db)):
    resp_dict = {"status": "success", "token": None, "error": None}
    token = request.token
    auth_token = decode_jwt(token, db)
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    resp_dict["token"] = auth_token

    return resp_dict

@auth_router.post('/check_auth')
async def check_auth(
    request: Request,
    db: Session = Depends(get_db),
    user_details: ResponseModel = Depends(verify_token)
):
    """
    Check authentication and return user details.
    Creates user if they don't exist in the database.
    """
    logger.info(f"User details fetched from draup api - {str(user_details)}")
    if user_details.status != "Success" or not user_details.data:
        logger.info(f"No user data found, returning empty response")
        return user_details.to_dict()

    try:
        user_data = user_details.data

        if not user_data.get("email"):
            logger.info(f"User Email not found, Throwing 401 error.")
            return ResponseModel(
                status="Failure", 
                error="Email not found in user data"
            ).to_dict()

        user_obj = db.query(User).filter(User.email == user_data["email"]).first()
        
        if not user_obj:
            if "group" not in user_data:
                user_data["group"] = "Admin"

            create_result = create_user(db, user_data)
            if create_result.get("status").lower() != "success":
                raise Exception(create_result["error"])
            
            user_obj = create_result["data"]
        is_demo_user = user_obj.email == "draup.demo@draup.com"
        company = (
            db.query(MasterCompany)
            .filter(MasterCompany.id == user_obj.company_id)
            .first()
        )
        user_obj.company_name = company.company_name if company else None
        user_obj.company_logo = company.logo if company else None
        exclude_fields = ["_sa_instance_state"]
        if is_demo_user:
            exclude_fields.append("company_logo")
        user_dict = user_obj.to_dict(exclude=exclude_fields)
        return ResponseModel(
            status="Success",
            data=UserResponse(**user_dict)
        ).to_dict()

    except Exception as e:
        logger.info(f"Error {str(e)} occurred while verifying user.")
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@auth_router.post("/update_user_details")
async def update_user_details(
    request: Request,
    email: EmailStr = Form(...),
    company_name: str = Form(...),
    username: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    theme_config: str = Form(None),
    image: Optional[UploadFile] = Form(None),
    db: Session = Depends(get_db)
):
    resp_obj = {"status": "success", "data": None, "errors": []}

    try:
        user = db.query(User).filter(User.email==email,
                                     User.username==username).first()
        if not user:
            resp_obj["status"] = "failure"
            resp_obj["errors"] = [f"User {username} not found"]
            return resp_obj
        
        if image:
            image_content = await image.read()
            file_extension = os.path.splitext(image.filename)[1] if image.filename else '.jpg'
            is_draup_user = email.endswith("@draup.com")
            if is_draup_user:
                unique_filename = f"{get_s3_environment()}/public/{user.username}{file_extension}"
            else:
                unique_filename = f"{get_s3_environment()}/public/{company_name}/{user.username}{file_extension}"

            file_obj = BytesIO(image_content)

            public_url = upload_to_s3_with_config(
                file=file_obj,
                key=unique_filename,
                is_public=True
            )

            if public_url:
                user.image = public_url
            else:
                resp_obj["status"] = "failure"
                resp_obj["errors"] = ["Failed to upload image to S3"]
                return resp_obj
        
        theme_config_dict = None
        if theme_config:
            theme_config_dict = json.loads(theme_config)
        user.first_name = first_name
        user.last_name = last_name
        user.theme_config = theme_config_dict
        db.commit()
        db.refresh(user)
        resp_obj["data"] = user 
    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"] = [str(e)]

    return resp_obj


@auth_router.post("/upload_to_s3")
async def upload_to_s3(
    file: UploadFile = File(...),
    key: str = Form(...),
    is_public: bool = Form(False),
    to_get_url: bool = Form(False),
    expiration_days: int = Form(7),
    bucket_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    resp_obj = {"status": "success", "data": None, "errors": []}
    
    try:
        file_content = await file.read()
        file_obj = BytesIO(file_content)
        
        result = upload_to_s3_with_config(
            file=file_obj,
            key=key,
            is_public=is_public,
            to_get_url=to_get_url,
            expiration_days=expiration_days,
            bucket_name=bucket_name
        )
        
        if result:
            resp_obj["data"] = {
                "url": result if isinstance(result, str) else None,
                "success": True,
                "key": key
            }
        else:
            resp_obj["status"] = "failure"
            resp_obj["errors"] = ["Failed to upload file to S3"]
    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"] = [str(e)]
        logger.error(f"Error uploading to S3: {str(e)}")
    
    return resp_obj


@auth_router.get('/auto_complete_username')
async def auto_complete_username(
    request: Request,
    draup_user: ResponseModel = Depends(verify_token),
    username: Optional[str] = None,
    user_group: Optional[Union[str, List[str]]] = None,
    db: Session = Depends(get_db)
):
    resp_obj = {"status": "success", "data": None, "errors": []}

    try:
        draup_user_data = draup_user.data
        user_obj = db.query(User).filter(User.email==draup_user_data["email"]).first()
        if user_group:
            valid_groups = ["Researcher", "Reviewer", "Admin", "Etter Generator", "Super Admin"]
            
            if isinstance(user_group, str):
                if ',' in user_group:
                    user_group_list = [group.strip() for group in user_group.split(',')]
                else:
                    user_group_list = [user_group]
            else:
                user_group_list = user_group
            
            invalid_groups = [group for group in user_group_list if group not in valid_groups]
            if invalid_groups:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid user groups: {invalid_groups}. Must be one of: Researcher, Reviewer, Admin, Etter Generator, Super Admin"
                )
        users = (
            db.query(User)
            .join(MasterCompany, User.company_id == MasterCompany.id)
            .filter(MasterCompany.company_name == user_obj.company.company_name)
        )

        if username:
            users = users.filter(User.username.ilike(f"%{username}%"))

        if user_group:
            if len(user_group_list) == 1:
                users = users.filter(User.group == user_group_list[0])
            else:
                users = users.filter(User.group.in_(user_group_list))

        users = users.limit(10).all()
        resp_obj["data"] = [{"user_name": user.username, "image": user.image} for user in users]
    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"] = [f"Error: {str(e)} occurred while fetching username."]
    return resp_obj


@auth_router.post('/get_image')
async def get_image(
    request: Request,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": [], "errors": []}
    try:
        body = await request.json()
        username = body.get("username", [])
        if not username:
            return resp_obj

        filters = [User.username == name for name in username]
        users = db.query(User).filter(or_(*filters)).all()
        resp_obj["data"] = [{"user_name": user.username, "image": user.image} for user in users]
    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"] = [f"Error: {str(e)} occurred while fetching username."]
    return resp_obj

#
# @auth_router.post('/create_initial_admin')
# async def create_initial_admin(
#         request: Request,
#         email: EmailStr = Form(..., description="Email of the admin user to be created"),
#         username: str = Form(...),
#         company_name: str = Form(...),
#         first_name: str = Form(...),
#         last_name: str = Form(...),
#         password: SecretStr = Form(..., description="Password for the admin user which must be at least 8 characters "
#                                              "long and contain uppercase, lowercase, number, and special character"),
#         is_active: bool = Form(True, description="Whether the admin user is active or not"),
#         image: Optional[UploadFile] = File(None, description="Profile image of the admin user"),
#         admin_secret_token: str = Header(..., description="Special token for creating initial admin"),
#         db: Session = Depends(get_db)
# ):
#     resp_obj = {"status": "success", "data": None, "errors": []}
#
#     try:
#         admin_secret_env = os.environ.get("ADMIN_SECRET")
#         if not admin_secret_env:
#             raise HTTPException(
#                 status_code=500,
#                 detail="Admin creation token not configured"
#             )
#
#         if admin_secret_token != admin_secret_env:
#             raise HTTPException(
#                 status_code=403,
#                 detail="Invalid admin creation token"
#             )
#
#         if not validate_password(password.get_secret_value()):
#             raise HTTPException(
#                 status_code=400,
#                 detail="Password must be at least 8 characters long and contain uppercase, lowercase, number, and special character"
#             )
#
#         user_data = {
#             "email": email,
#             "username": username,
#             "company_name": company_name,
#             "first_name": first_name,
#             "last_name": last_name,
#             "password": password,
#             "group": "Admin",
#             "image": image,
#             "is_active": is_active
#         }
#         user_obj = await add_new_user(user_data, db)
#
#         resp_obj["data"] = user_obj
#
#     except Exception as e:
#         resp_obj["status"] = "failure"
#         resp_obj["errors"] = [str(e)]
#
#     return resp_obj
#
# @auth_router.post('/logout')
# def logout(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(verify_token),
#     authorization: str = Header(..., description="Bearer token")
# ):
#     resp_obj = {"status": "success", "data": None, "errors": []}
#
#     try:
#         if not authorization.startswith("Bearer "):
#             raise HTTPException(
#                 status_code=401,
#                 detail="Invalid authorization header format"
#             )
#
#         token = authorization.replace("Bearer ", "")
#         blacklist_token(token, current_user.id, db)
#
#         resp_obj["data"] = {
#             "message": "Successfully logged out",
#             "user_email": current_user.email
#         }
#
#     except Exception as e:
#         resp_obj["status"] = "failure"
#         resp_obj["errors"] = [str(e)]
#
#     return JSONResponse(resp_obj)
#
#
# @auth_router.post('/get_login_type')
# def get_login_type(
#     user_data: OTPRequest,
#     db: Session = Depends(get_db)
# ):
#     resp_obj = {"status": "success", "data": None, "errors": []}
#
#     try:
#         user = db.query(User).filter(User.email == user_data.email).first()
#         if not user:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["User not found"]
#             return resp_obj
#
#         login_type = user.login_type
#
#         if login_type == "otp":
#             otp = create_otp_for_user(user_data.email, db)
#             resp_obj["data"] = {
#                 "login_type": login_type,
#                 "message": "OTP sent to your email"
#             }
#         elif login_type == "sso":
#             credentials = get_sso_credentials(user.company_id, db)
#             if not credentials:
#                 resp_obj["status"] = "failure"
#                 resp_obj["errors"] = ["SSO credentials not configured for this company"]
#                 return resp_obj
#
#             resp_obj["data"] = {
#                 "login_type": login_type,
#                 "sso_credentials": {
#                     "client_id": credentials.client_id,
#                     "redirect_uri": credentials.redirect_uri,
#                     "auth_uri": credentials.auth_uri,
#                     "token_uri": credentials.token_uri,
#                     "userinfo_uri": credentials.userinfo_uri
#                 }
#             }
#         else:
#             resp_obj["data"] = {
#                 "login_type": login_type
#             }
#
#     except Exception as e:
#         resp_obj["status"] = "failure"
#         resp_obj["errors"] = [str(e)]
#
#     return resp_obj
#
#
# @auth_router.post('/sso_user_details')
# def get_sso_user_details(
#     email: EmailStr = Form(...),
#     sso_token: str = Form(...),
#     db: Session = Depends(get_db)
# ):
#     resp_obj = {"status": "success", "data": None, "errors": []}
#
#     try:
#         user = db.query(User).filter(User.email == email).first()
#         if not user:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["User not found"]
#             return resp_obj
#
#         if user.login_type != "sso":
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["User is not configured for SSO login"]
#             return resp_obj
#
#         credentials = get_sso_credentials(user.company_id, db)
#         if not credentials:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["SSO credentials not configured for this company"]
#             return resp_obj
#
#         access_token = create_access_token(
#             data={"sub": user.email},
#             expires_delta=timedelta(days=7)
#         )
#
#         company = db.query(MasterCompany).filter(MasterCompany.id == user.company_id).first()
#         user.company_name = company.company_name if company else None
#         user.company_logo = company.logo if company else None
#
#         exclude_fields = ['password', 'company_id', '_sa_instance_state']
#         user_dict = user.to_dict(exclude=exclude_fields)
#
#         resp_obj["data"] = {
#             "access_token": access_token,
#             "token_type": "bearer",
#             "user_data": UserResponse(**user_dict)
#         }
#
#     except Exception as e:
#         resp_obj["status"] = "failure"
#         resp_obj["errors"] = [str(e)]
#
#     return resp_obj
#
#
# @auth_router.post('/request_otp')
# def request_otp(
#     user_data: OTPRequest,
#     db: Session = Depends(get_db)
# ):
#     resp_obj = {"status": "success", "data": None, "errors": []}
#
#     try:
#         otp = create_otp_for_user(user_data.email, db)
#
#         resp_obj["data"] = {
#             "message": "OTP generated successfully",
#             "email": user_data.email
#         }
#
#     except Exception as e:
#         resp_obj["status"] = "failure"
#         resp_obj["errors"] = [str(e)]
#
#     return resp_obj
#
#
# @auth_router.post('/resend_otp')
# def resend_otp(
#     user_data: OTPRequest,
#     db: Session = Depends(get_db)
# ):
#     resp_obj = {"status": "success", "data": None, "errors": []}
#
#     try:
#         otp = resend_otp_for_user(user_data.email, db)
#
#         resp_obj["data"] = {
#             "message": "OTP resent successfully",
#             "email": user_data.email
#         }
#
#     except Exception as e:
#         resp_obj["status"] = "failure"
#         resp_obj["errors"] = [str(e)]
#
#     return resp_obj
#
#
# @auth_router.post('/validate_otp')
# def validate_otp_login(
#     user_data: OTPValidation,
#     db: Session = Depends(get_db)
# ):
#     resp_obj = {"status": "success", "data": None, "errors": []}
#
#     try:
#         if not validate_otp(user_data.email, user_data.otp, db):
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["Invalid or expired OTP"]
#             return resp_obj
#
#         user = db.query(User).filter(User.email == user_data.email).first()
#         if not user:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["User not found"]
#             return resp_obj
#
#         access_token = create_access_token(
#             data={"sub": user.email},
#             expires_delta=timedelta(days=7)
#         )
#
#         company = db.query(MasterCompany).filter(MasterCompany.id == user.company_id).first()
#         user.company_name = company.company_name if company else None
#         user.company_logo = company.logo if company else None
#
#         exclude_fields = ['password', 'company_id', '_sa_instance_state']
#         user_dict = user.to_dict(exclude=exclude_fields)
#
#         resp_obj["data"] = {
#             "access_token": access_token,
#             "token_type": "bearer",
#             "user_data": UserResponse(**user_dict)
#         }
#
#     except Exception as e:
#         resp_obj["status"] = "failure"
#         resp_obj["errors"] = [str(e)]
#
#     return resp_obj
#
#
# @auth_router.post('/sso_login')
# def sso_login(
#     user_data: SSOLogin,
#     db: Session = Depends(get_db)
# ):
#     resp_obj = {"status": "success", "data": None, "errors": []}
#
#     try:
#         user = db.query(User).filter(User.email == user_data.email).first()
#         if not user:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["User not found"]
#             return resp_obj
#
#         if user.login_type != "sso":
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["User is not configured for SSO login"]
#             return resp_obj
#
#         access_token = create_access_token(
#             data={"sub": user.email},
#             expires_delta=timedelta(days=7)
#         )
#
#         company = db.query(MasterCompany).filter(MasterCompany.id == user.company_id).first()
#         user.company_name = company.company_name if company else None
#         user.company_logo = company.logo if company else None
#
#         exclude_fields = ['password', 'company_id', '_sa_instance_state']
#         user_dict = user.to_dict(exclude=exclude_fields)
#
#         resp_obj["data"] = {
#             "access_token": access_token,
#             "token_type": "bearer",
#             "user_data": UserResponse(**user_dict)
#         }
#
#     except Exception as e:
#         resp_obj["status"] = "failure"
#         resp_obj["errors"] = [str(e)]
#
#     return resp_obj
#
#
# @auth_router.post('/create_sso_credentials')
# def create_sso_credentials_api(
#     company_id: int = Form(...),
#     client_id: str = Form(...),
#     client_secret: str = Form(...),
#     redirect_uri: str = Form(...),
#     auth_uri: str = Form(...),
#     token_uri: str = Form(...),
#     userinfo_uri: str = Form(...),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(verify_token)
# ):
#     resp_obj = {"status": "success", "data": None, "errors": []}
#
#     try:
#         if current_user.group != "Admin":
#             raise HTTPException(status_code=403, detail="Only admins can create SSO credentials")
#
#         company = db.query(MasterCompany).filter(MasterCompany.id == company_id).first()
#         if not company:
#             raise HTTPException(status_code=404, detail="Company not found")
#
#         credentials_data = {
#             "company_id": company_id,
#             "client_id": client_id,
#             "client_secret": client_secret,
#             "redirect_uri": redirect_uri,
#             "auth_uri": auth_uri,
#             "token_uri": token_uri,
#             "userinfo_uri": userinfo_uri
#         }
#
#         credentials = create_sso_credentials(credentials_data, db)
#
#         resp_obj["data"] = {
#             "id": credentials.id,
#             "company_id": credentials.company_id,
#             "company_name": company.company_name,
#             "client_id": credentials.client_id,
#             "redirect_uri": credentials.redirect_uri,
#             "auth_uri": credentials.auth_uri,
#             "token_uri": credentials.token_uri,
#             "userinfo_uri": credentials.userinfo_uri,
#             "created_at": credentials.created_at,
#             "updated_at": credentials.updated_at
#         }
#
#     except Exception as e:
#         resp_obj["status"] = "failure"
#         resp_obj["errors"] = [str(e)]
#
#     return resp_obj
#
#
# @auth_router.get('/get_sso_credentials/{company_id}')
# def get_sso_credentials_api(
#     company_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(verify_token)
# ):
#     resp_obj = {"status": "success", "data": None, "errors": []}
#
#     try:
#         if current_user.group != "Admin":
#             raise HTTPException(status_code=403, detail="Only admins can view SSO credentials")
#
#         company = db.query(MasterCompany).filter(MasterCompany.id == company_id).first()
#         if not company:
#             raise HTTPException(status_code=404, detail="Company not found")
#
#         credentials = get_sso_credentials(company_id, db)
#         if not credentials:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["SSO credentials not found for this company"]
#             return resp_obj
#
#         resp_obj["data"] = {
#             "id": credentials.id,
#             "company_id": credentials.company_id,
#             "company_name": company.company_name,
#             "client_id": credentials.client_id,
#             "redirect_uri": credentials.redirect_uri,
#             "auth_uri": credentials.auth_uri,
#             "token_uri": credentials.token_uri,
#             "userinfo_uri": credentials.userinfo_uri,
#             "created_at": credentials.created_at,
#             "updated_at": credentials.updated_at
#         }
#
#     except Exception as e:
#         resp_obj["status"] = "failure"
#         resp_obj["errors"] = [str(e)]
#
#     return resp_obj
#
#
# @auth_router.get('/get_sso_credentials_by_user')
# def get_sso_credentials_by_user_api(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(verify_token)
# ):
#     resp_obj = {"status": "success", "data": None, "errors": []}
#
#     try:
#         credentials = get_sso_credentials(current_user.company_id, db)
#         if not credentials:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["SSO credentials not found for your company"]
#             return resp_obj
#
#         resp_obj["data"] = {
#             "id": credentials.id,
#             "company_id": credentials.company_id,
#             "client_id": credentials.client_id,
#             "redirect_uri": credentials.redirect_uri,
#             "auth_uri": credentials.auth_uri,
#             "token_uri": credentials.token_uri,
#             "userinfo_uri": credentials.userinfo_uri
#         }
#
#     except Exception as e:
#         resp_obj["status"] = "failure"
#         resp_obj["errors"] = [str(e)]
#
#     return resp_obj
#
#
# @auth_router.post('/update_user_login_type')
# def update_user_login_type(
#     email: EmailStr = Form(...),
#     login_type: str = Form(...),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(verify_token)
# ):
#     resp_obj = {"status": "success", "data": None, "errors": []}
#
#     try:
#         if current_user.group != "Admin":
#             raise HTTPException(status_code=403, detail="Only admins can update user login type")
#
#         if login_type not in ["otp", "sso"]:
#             raise HTTPException(status_code=400, detail="Login type must be either 'otp' or 'sso'")
#
#         user = db.query(User).filter(User.email == email).first()
#         if not user:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["User not found"]
#             return resp_obj
#
#         user.login_type = login_type
#         db.commit()
#         db.refresh(user)
#
#         resp_obj["data"] = {
#             "email": user.email,
#             "login_type": user.login_type
#         }
#
#     except Exception as e:
#         resp_obj["status"] = "failure"
#         resp_obj["errors"] = [str(e)]
#
#     return resp_obj
#
#
# @auth_router.post('/sso/callback')
# def sso_callback(
#     callback_data: SSOCallbackRequest,
#     db: Session = Depends(get_db)
# ):
#     resp_obj = {"status": "success", "data": None, "errors": []}
#
#     try:
#         credentials = db.query(SSOCredentials).filter(
#             SSOCredentials.client_id == callback_data.client_id,
#             SSOCredentials.redirect_uri == callback_data.redirect_uri
#         ).first()
#
#         if not credentials:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["Invalid SSO credentials"]
#             return resp_obj
#
#         token_data = {
#             'grant_type': 'authorization_code',
#             'code': callback_data.code,
#             'client_id': credentials.client_id,
#             'client_secret': credentials.client_secret,
#             'redirect_uri': credentials.redirect_uri
#         }
#
#         token_response = requests.post(credentials.token_uri, data=token_data)
#
#         if not token_response.ok:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["Failed to exchange authorization code for token"]
#             return resp_obj
#
#         token_info = token_response.json()
#         access_token = token_info.get('access_token')
#
#         if not access_token:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["No access token received from SSO provider"]
#             return resp_obj
#
#         headers = {'Authorization': f'Bearer {access_token}'}
#         userinfo_response = requests.get(credentials.userinfo_uri, headers=headers)
#
#         if not userinfo_response.ok:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["Failed to get user information from SSO provider"]
#             return resp_obj
#
#         userinfo = userinfo_response.json()
#         user_email = userinfo.get('email')
#
#         if not user_email:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["No email found in user information"]
#             return resp_obj
#
#         user = db.query(User).filter(User.email == user_email).first()
#         if not user:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["User not found in our system"]
#             return resp_obj
#
#         if user.login_type != "sso":
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["User is not configured for SSO login"]
#             return resp_obj
#
#         if user.company_id != credentials.company_id:
#             resp_obj["status"] = "failure"
#             resp_obj["errors"] = ["User does not belong to the company with these SSO credentials"]
#             return resp_obj
#
#         app_access_token = create_access_token(
#             data={"sub": user.email},
#             expires_delta=timedelta(days=7)
#         )
#
#         company = db.query(MasterCompany).filter(MasterCompany.id == user.company_id).first()
#         user.company_name = company.company_name if company else None
#         user.company_logo = company.logo if company else None
#
#         exclude_fields = ['password', 'company_id', '_sa_instance_state']
#         user_dict = user.to_dict(exclude=exclude_fields)
#
#         resp_obj["data"] = {
#             "access_token": app_access_token,
#             "token_type": "bearer",
#             "user_data": UserResponse(**user_dict)
#         }
#
#     except Exception as e:
#         resp_obj["status"] = "failure"
#         resp_obj["errors"] = [str(e)]
#
#     return resp_obj
