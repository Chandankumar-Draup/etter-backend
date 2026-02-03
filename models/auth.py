from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum, ForeignKey, Text, DateTime, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone
from settings.database import Base
from sqlalchemy.orm import relationship
from typing import Dict, Any


class GroupType(str, SQLEnum):
    RESEARCHER = "Researcher"
    REVIEWER = "Reviewer"
    ADMIN = "Admin"
    SUPER_ADMIN = "Super Admin"
    ETTER_GENERATOR = "Etter Generator"


class LoginType(str, SQLEnum):
    OTP = "otp"
    SSO = "sso"


class User(Base):
    __tablename__ = 'etter_users'
    __table_args__ = (
        UniqueConstraint('email'),
        Index('idx_etter_users_email', 'email'),
        Index('idx_etter_users_company_id', 'company_id'),
        Index('idx_etter_users_username', 'username'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    company_id = Column(Integer, ForeignKey('iris1.iris1_mastercompany.id'), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    password = Column(String(128), nullable=False)
    group = Column(SQLEnum(GroupType.RESEARCHER, GroupType.REVIEWER, GroupType.ADMIN, GroupType.SUPER_ADMIN, GroupType.ETTER_GENERATOR,
                           name='user_group_type'), default=GroupType.RESEARCHER, nullable=False)
    image = Column(String(400), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    company = relationship('MasterCompany', backref='users')
    theme_config = Column(JSONB, nullable=True, default={})
    login_type = Column(
        SQLEnum(LoginType.OTP, LoginType.SSO, name="login_type"),
        default=LoginType.OTP,
        nullable=False,
    )
    workflow_history = relationship('UserWorkflowHistory', foreign_keys='UserWorkflowHistory.user_id', back_populates='user')
    approver_history = relationship('UserWorkflowHistory', foreign_keys='UserWorkflowHistory.approver_id', back_populates='approver')
    otp_records = relationship('UserOTP', back_populates='user')

    def to_dict(self, exclude: list = None) -> Dict[str, Any]:
        if exclude is None:
            exclude = []
            
        return {
            key: value for key, value in self.__dict__.items()
            if not key.startswith('_') and key not in exclude
        }


class UserOTP(Base):
    __tablename__ = 'user_otp'
    __table_args__ = {'schema': 'etter'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('etter.etter_users.id'), nullable=False)
    otp = Column(String(6), nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False)
    valid_till = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now(tz=timezone.utc), nullable=False)
    
    user = relationship('User', back_populates='otp_records')


class SSOCredentials(Base):
    __tablename__ = 'sso_credentials'
    __table_args__ = {'schema': 'etter'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('iris1.iris1_mastercompany.id'), nullable=False)
    client_id = Column(String(255), nullable=False)
    client_secret = Column(String(500), nullable=False)
    redirect_uri = Column(String(500), nullable=False)
    auth_uri = Column(String(500), nullable=False)
    token_uri = Column(String(500), nullable=False)
    userinfo_uri = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.now(tz=timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(tz=timezone.utc), onupdate=datetime.now(tz=timezone.utc), nullable=False)
    
    company = relationship('MasterCompany', backref='sso_credentials')


class TokenBlacklist(Base):
    __tablename__ = 'token_blacklist'
    __table_args__ = {'schema': 'etter'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(500), unique=True, nullable=False)
    blacklisted_at = Column(DateTime, default=datetime.now(tz=timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    user_id = Column(Integer, ForeignKey('etter.etter_users.id'), nullable=False)
    
    user = relationship('User', backref='blacklisted_tokens')
    