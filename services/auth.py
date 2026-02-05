from fastapi import HTTPException, Security, status
from common.logger import logger
from models.etter import MasterCompany
from models.auth import User
import bcrypt
from sqlalchemy.orm import Session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from constants.auth import DRAUP_API, CLIENT_ID, CLIENT_SECRET, TEMP_AUTH_TOKEN, ENV
from services.redis_store import get_redis_qa_login_client, get_cache_data
import json
# from api.user_management import generate_random_password
# import jwt as PyJWT
# from datetime import datetime, timedelta, UTC
# from typing import Optional, Dict, Any
# from sqlalchemy.orm import Session
# from settings.database import get_db
# from models.auth import User, TokenBlacklist, UserOTP, SSOCredentials, LoginType
# import bcrypt
# import re
import secrets
import string
import base64
from datetime import datetime, timedelta, UTC
import jwt
from jwt import PyJWTError
from typing import Optional

import requests
from typing import Dict, Any
from fastapi.responses import JSONResponse
import os
import random
from services.email_service import email_service

# security = HTTPBearer()
#
SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1
# REFRESH_TOKEN_EXPIRE_DAYS = 7
#
# class TokenError(Exception):
#     """Base exception for token-related errors"""
#     pass
#
# class TokenExpiredError(TokenError):
#     """Raised when token has expired"""
#     pass
#
# class TokenInvalidError(TokenError):
#     """Raised when token is invalid"""
#     pass
#
# def validate_password(password: str) -> bool:
#     """
#     Validate password against common security rules:
#     - At least 8 characters
#     - At least one uppercase letter
#     - At least one lowercase letter
#     - At least one number
#     - At least one special character
#     """
#     if len(password) < 8:
#         return False
#     if not re.search(r"[A-Z]", password):
#         return False
#     if not re.search(r"[a-z]", password):
#         return False
#     if not re.search(r"\d", password):
#         return False
#     if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
#         return False
#     return True


class ResponseModel:
    def __init__(self, status: str = "Success", data: dict = None, error: str = None):
        self.status = status
        self.data = data
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "data": self.data,
            "error": self.error
        }

    def to_json_response(self, status_code: int = 200) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content=self.to_dict()
        )

from functools import wraps
from fastapi import Request

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> ResponseModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
    response = ResponseModel()
    token = credentials.credentials
    user_details_api = f"{DRAUP_API}/service/client/user/authenticate/"
    
    if ENV == "qa":
        try:
            redis_client = get_redis_qa_login_client()
            cached_data = get_cache_data(redis_client, token)
            
            if cached_data:
                logger.info(f"Cache hit for token in QA environment")
                response.data = cached_data
                return response
            else:
                logger.info(f"Cache miss for token in QA environment, making API call")
        except Exception as redis_error:
            logger.warning(f"Redis error in verify_token, falling back to API call: {str(redis_error)}")
    
    headers = {
        "Authorization": "Bearer " + token,
        "product-id": "5",
        "Content-Type": "application/json",
    }
    logger.info(f"Hitting draup api to get user details: {user_details_api}")
    payload = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
    user_response = requests.post(user_details_api, headers=headers, json=payload)
    logger.info(f"Response from draup api: {user_response.status_code}")
    logger.info(f"Response content from draup api: {user_response.content}")
    
    if user_response.status_code == 200:
        user_data = user_response.json()
        response.data = user_data
        
        if ENV == "qa":
            try:
                redis_client = get_redis_qa_login_client()
                redis_client.set(token, json.dumps(user_data))
                logger.info(f"Cached user response for token in QA environment")
            except Exception as cache_error:
                logger.warning(f"Failed to cache user response: {str(cache_error)}")
    else:
        logger.info(f"Error occurred while fetching user details from draup api")
        # Local development: skip external auth when Draup API is unreachable
        if _is_local_environment():
            logger.info("Local dev mode: skipping Draup auth, using fallback credentials")
            response.data = {
                "user_id": 1,
                "company_id": os.environ.get("ETTER_LOCAL_TENANT_ID", "1"),
                "email": "local@dev",
                "group": "Admin",
            }
            return response
        raise credentials_exception

    return response


def _is_local_environment() -> bool:
    """Check if running in local development (not QA/prod).

    Uses ETTER_DB_HOST: empty or localhost means local.
    QA/prod always have a real DB host set.
    """
    db_host = os.environ.get("ETTER_DB_HOST", "").lower()
    return not db_host or db_host == "localhost" or "127.0.0.1" in db_host


def create_jwt_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a new JWT token with the given data and expiration
    """
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"product": "workato", "exp": expire})

        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    except Exception as e:
        raise Exception(f"Error creating token: {str(e)}")

def decode_jwt(token: str, db: Session) -> str:
    temp_Token = ""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if "username" in payload:
            current_user = (
                db.query(User).filter(User.email == payload["username"]).first()
            )
            if current_user:
                return TEMP_AUTH_TOKEN

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    return temp_Token

def generate_username_from_email(email: str, db: Session):
    email_part = email.split("@")[0]
    base_username = email_part.lower()
    username = base_username

    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1

    return username

def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for _ in range(length))


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def create_user(db, user_data):
    resp_obj = {"status": "success", "data": None, "errors": []}
    try:
        theme_config_dict = {
              "theme": "dark",
              "isSystemTheme": False
            }
        password = generate_random_password()
        hashed_password = hash_password(password)
        user_data = {
            "email": user_data["email"],
            "username": generate_username_from_email(user_data["email"], db),
            "company_name": user_data.get("company_name", "Draup"),
            "first_name": user_data.get("firstName"),
            "last_name": user_data.get("lastName"),
            "password": hashed_password,
            "group": user_data.get("group", "Admin"),
            "image": user_data.get("image"),
            "is_active": user_data.get("is_active", True),
            "theme_config": theme_config_dict,
        }
        user_obj = add_new_user(db, user_data)

        resp_obj["data"] = user_obj

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["error"] = str(e)

    return resp_obj

def add_new_user(db, user_data):
    company_obj = (
        db.query(MasterCompany)
        .filter(MasterCompany.company_name == user_data["company_name"])
        .first()
    )
    if not company_obj:
        raise Exception(f"Company with name {user_data['company_name']} not found")
    image_path = None
    if user_data["image"]:
        image_content = user_data["image"].read()
        base64_image = base64.b64encode(image_content).decode('utf-8')
        image_path = f"data:{user_data['image'].content_type};base64,{base64_image}"
    user_data["company_id"] = company_obj.id
    del user_data["company_name"]

    user_data["image"] = image_path if image_path else None

    user_obj = User(**user_data)
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)

    return user_obj
