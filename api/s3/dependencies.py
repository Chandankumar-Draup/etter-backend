from typing import Generator
from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

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


def get_auth_context(
    draup_user: ResponseModel = Depends(verify_token)
) -> AuthContext:
    """
    Extract authentication context from verified token.
    Uses the same pattern as api/etter_apis.py and api/auth.py
    
    Args:
        draup_user: Verified user details from Draup API
        
    Returns:
        AuthContext with user_id, tenant_id, email, and group
        
    Raises:
        HTTPException: If authentication fails or required fields are missing
    """
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
    
    user_id = draup_user_data["user_id"]
    tenant_id = str(draup_user_data["company_id"])
    email = draup_user_data.get("email", "")
    group = draup_user_data.get("group", "Researcher")
    
    return AuthContext(
        user_id=user_id,
        tenant_id=tenant_id,
        email=email,
        group=group
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

