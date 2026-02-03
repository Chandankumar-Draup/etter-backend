from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from fastapi import UploadFile


class SSODetails(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str
    auth_uri: str
    token_uri: str
    userinfo_uri: str


class UserListResponse(BaseModel):
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    image: Optional[str] = None
    is_active: bool
    id: int
    group: str
    company_name: Optional[str] = None
    company_id: Optional[int] = None
    company_logo: Optional[str] = None
    sso_type: Optional[str] = None
    sso_details: Optional[SSODetails] = None


class PaginatedUserResponse(BaseModel):
    users: List[UserListResponse]
    total_count: int
    page: int
    size: int
    total_pages: int
    

class GetUsersRequest(BaseModel):
    page: int = 1
    size: int = 50
    company_name: Optional[str] = None
    email: Optional[str] = None

class CreateUserRequest(BaseModel):
    email: EmailStr
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    group: str


class CreateUserResponse(BaseModel):
    id: int
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    company_id: int
    group: str
    is_active: bool


class UpdateUserRequest(BaseModel):
    group: Optional[str] = None
    is_active: Optional[bool] = None
    company_name: Optional[str] = None
    sso_details: Optional[SSODetails] = None


class UpdateCompanyImagesRequest(BaseModel):
    light_theme_image: Optional[UploadFile] = None
    dark_theme_image: Optional[UploadFile] = None


class CompanyImagesResponse(BaseModel):
    light_theme_image: Optional[str] = None
    dark_theme_image: Optional[str] = None
