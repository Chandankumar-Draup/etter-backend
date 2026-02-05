from typing import Generator, Optional
from uuid import UUID
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os

from settings.database import get_db
from services.auth import verify_token, ResponseModel
from api.s3.infra.db.uow import UnitOfWork
from api.s3.infra.s3.s3_management_service import S3ManagementService


class AuthContext:
    """Authentication context extracted from JWT token."""

    def __init__(self, user_id: int, tenant_id: str, email: str, group: str):
        self.user_id_int = user_id
        self.user_id = UUID(int=user_id)  # Convert int to UUID for consistency
        self.tenant_id = tenant_id
        self.email = email
        self.group = group
        self.is_admin = group in ["Super Admin", "Admin"]


def _is_local_environment() -> bool:
    """Check if running in local development (not QA/prod)."""
    db_host = os.environ.get("ETTER_DB_HOST", "").lower()
    return not bool(db_host and db_host != "localhost" and "127.0.0.1" not in db_host)


# Optional security - doesn't auto-raise 403 when no Bearer token is provided
_optional_security = HTTPBearer(auto_error=False)


def get_auth_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_optional_security),
) -> AuthContext:
    """
    Extract authentication context from verified token.

    In local development, returns default context when no auth header is provided.
    In QA/prod, always requires valid Draup API authentication.
    """
    if credentials:
        # Auth header provided - validate through Draup API
        draup_user = verify_token(credentials)

        if draup_user.status != "Success" or not draup_user.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )

        draup_user_data = draup_user.data

        if not draup_user_data.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )

        if not draup_user_data.get("company_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not associated with a company"
            )

        return AuthContext(
            user_id=draup_user_data["user_id"],
            tenant_id=str(draup_user_data["company_id"]),
            email=draup_user_data.get("email", ""),
            group=draup_user_data.get("group", "Researcher"),
        )

    # No credentials provided
    if _is_local_environment():
        default_tenant = os.environ.get("ETTER_LOCAL_TENANT_ID", "1")
        return AuthContext(
            user_id=1,
            tenant_id=default_tenant,
            email="local@dev.com",
            group="Admin",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )


def get_uow(db: Session = Depends(get_db)) -> Generator[UnitOfWork, None, None]:
    """
    Dependency to get Unit of Work instance.
    
    Args:
        db: Database session
        
    Yields:
        UnitOfWork instance
    """
    uow = UnitOfWork(db)
    try:
        yield uow
    finally:
        pass


# Singleton S3 service
_s3_service = None


def get_s3_service() -> S3ManagementService:
    """
    Dependency to get S3 Management Service (singleton).
    
    Returns:
        S3ManagementService instance
    """
    global _s3_service
    if _s3_service is None:
        _s3_service = S3ManagementService()
    return _s3_service

