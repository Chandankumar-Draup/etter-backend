from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, text
from sqlalchemy.orm import relationship
from settings.database import Base


class BaseModel(Base):
    __abstract__ = True
    
    created_by = Column(String(255), nullable=True)
    modified_by = Column(String(255), nullable=True)
    created_on = Column(DateTime, server_default=text('now()'), nullable=False)
    modified_on = Column(DateTime, server_default=text('now()'), onupdate=datetime.utcnow, nullable=False)


class ApproverModel(BaseModel):
    __abstract__ = True
    
    approver_id = Column(
        Integer,
        ForeignKey('etter.etter_users.id'),
        nullable=True
    )
    approval_status = Column(
        String(50),
        server_default="pending",
        nullable=False
    )
    approved_on = Column(DateTime, nullable=True)
