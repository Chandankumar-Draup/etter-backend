from pydantic import BaseModel, EmailStr
from fastapi import UploadFile
from typing import Optional


class UserResponse(BaseModel):
    email: EmailStr
    company_name: str
    company_id: int
    company_logo: Optional[str] = None
    first_name: str
    last_name: str
    username: str
    group: str
    image: Optional[str | None] = None
    theme_config: dict | None = None
    is_active: bool

class CreateToken(BaseModel):
    username: str

class Token(BaseModel):
    token: str
#
# class UserLogin(BaseModel):
#     email: EmailStr
#     password: str
#
#
# class OTPRequest(BaseModel):
#     email: EmailStr
#
#
# class OTPValidation(BaseModel):
#     email: EmailStr
#     otp: str
#
#
# class SSOLogin(BaseModel):
#     email: EmailStr
#     sso_token: str
#
#
# class SSOCallbackRequest(BaseModel):
#     code: str
#     client_id: str
#     redirect_uri: str
#
#
# class LoginTypeResponse(BaseModel):
#     login_type: str
#
#
# class SSOCredentialsResponse(BaseModel):
#     client_id: str
#     redirect_uri: str
#     auth_uri: str
#     token_uri: str
#     userinfo_uri: str
#
#
# class LoginTypeWithSSOResponse(BaseModel):
#     login_type: str
#     sso_credentials: Optional[SSOCredentialsResponse] = None
