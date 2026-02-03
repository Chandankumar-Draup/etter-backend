"""
Document Extraction Models

Database models for tracking extraction sessions and their results.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, UniqueConstraint, Text, ARRAY, Boolean, Table
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID
from settings.database import Base
from models.base_models import ApproverModel, BaseModel
import enum
import uuid


class ExtractionSessionStatus(str, enum.Enum):
    """Status of an extraction session."""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class ExtractionStatus(str, enum.Enum):
    """Status of a document extraction."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ApprovalStatus(str, enum.Enum):
    """Approval status for extracted documents."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RoleTaxonomyStatus(str, enum.Enum):
    """Status for role taxonomy records."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVIEW = "review"


class ExtractionSession(Base):
    """
    Tracks a session of document uploads for extraction.
    
    A session groups multiple documents for a user, allowing monitoring
    of progress even after page refresh.
    """
    __tablename__ = 'etter_extraction_session'
    __table_args__ = {'schema': 'etter'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Integer,
        ForeignKey('etter.etter_users.id'),
        nullable=False
    )
    approver_id = Column(
        Integer,
        ForeignKey('etter.etter_users.id'),
        nullable=True
    )
    approved_at = Column(DateTime, nullable=True)
    status = Column(
        Enum(ExtractionSessionStatus),
        default=ExtractionSessionStatus.ACTIVE,
        nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = relationship(
        'ExtractedDocument',
        back_populates='session',
        cascade='all, delete-orphan'
    )
    user = relationship('User', foreign_keys=[user_id], backref='extraction_sessions')
    approver = relationship('User', foreign_keys=[approver_id], backref='approved_extraction_sessions')


class ExtractedDocument(ApproverModel):
    """
    Stores extraction results for a single document.
    
    Links to the original document via document_id (from S3 upload service).
    Stores tasks, skills, stages extracted by Draup World Model API.
    """
    __tablename__ = 'etter_extracted_document'
    __table_args__ = {'schema': 'etter'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey('etter.etter_extraction_session.id'),
        nullable=False
    )
    document_id = Column(UUID(as_uuid=True), nullable=False)
    document_name = Column(String(500), nullable=True)

    status = Column(
        Enum(ExtractionStatus),
        default=ExtractionStatus.PENDING,
        nullable=False
    )
    error_message = Column(String(1000), nullable=True)

    document_type = Column(String(50), nullable=True)
    extraction_confidence = Column(Integer, nullable=True)
    extraction_metadata = Column(JSONB, nullable=True)
    tasks = Column(JSONB, nullable=True)
    skills = Column(JSONB, nullable=True)
    stages = Column(JSONB, nullable=True)
    task_to_skill = Column(JSONB, nullable=True)
    roles = Column(JSONB, nullable=True)

    approval_status = Column(
        Enum(ApprovalStatus),
        default=ApprovalStatus.PENDING,
        nullable=False
    )

    session = relationship('ExtractionSession', back_populates='documents')


class RoleTaxonomy(ApproverModel):
    """
    Stores role taxonomy/classification data for job descriptions and roles.
    
    Links to company via MasterCompany and user via User.
    Contains job-related fields like job title, job family, skills, etc.
    """
    __tablename__ = 'etter_role_taxonomy'
    __table_args__ = (
        UniqueConstraint('company_id', 'job_title', 'job_family', 'occupation', name='uix_role_taxonomy_company_job_family_occupation'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(
        Integer,
        ForeignKey('iris1.iris1_mastercompany.id'),
        nullable=False
    )
    job_id = Column(String(250), nullable=True, server_default="")
    job_role = Column(String(250), nullable=True, server_default="")
    job_title = Column(String(250), nullable=False, server_default="")
    occupation = Column(String(250), nullable=False, server_default="")
    occupation_id = Column(
        Integer,
        ForeignKey('etter.etter_master_company_role_occupation.id'),
        nullable=True
    )
    job_family = Column(String(250), nullable=False, server_default="")
    job_family_id = Column(
        Integer,
        ForeignKey('etter.etter_master_company_role_job_family.id'),
        nullable=True
    )
    job_level = Column(String(250), nullable=True, server_default="")
    job_track = Column(String(250), nullable=True, server_default="")
    job_track_id = Column(
        Integer,
        ForeignKey('etter.etter_master_company_role_job_track.id'),
        nullable=True
    )
    management_level = Column(String(250), nullable=True)
    management_level_id = Column(
        Integer,
        ForeignKey('etter.etter_master_company_role_management_level.id'),
        nullable=True
    )
    pay_grade = Column(String(250), nullable=True)
    draup_role = Column(String(250), nullable=True)
    job_description = Column(Text, nullable=True, server_default="")
    general_summary = Column(Text, nullable=True, server_default="")
    duties_responsibilities = Column(Text, nullable=True, server_default="")
    work_experience = Column(Text, nullable=True, server_default="")
    skills = Column(ARRAY(String), nullable=True, server_default="{}")
    others = Column(JSONB, nullable=True)
    source = Column(String(250), nullable=False, server_default="User")
    user_id = Column(
        Integer,
        ForeignKey('etter.etter_users.id'),
        nullable=False
    )
    
    company = relationship('MasterCompany')
    user = relationship('User', foreign_keys=[user_id], backref='role_taxonomies')
    approver = relationship('User', foreign_keys='RoleTaxonomy.approver_id', backref='approved_role_taxonomies')
    occupation_master = relationship('MasterCompanyRoleOccupation', foreign_keys=[occupation_id])
    job_family_master = relationship('MasterCompanyRoleJobFamily', foreign_keys=[job_family_id])
    job_track_master = relationship('MasterCompanyRoleJobTrack', foreign_keys=[job_track_id])
    management_level_master = relationship('MasterCompanyRoleManagementLevel', foreign_keys=[management_level_id])


class MasterSkillTaxonomyCategories(BaseModel):
    """
    Master table for skill taxonomy categories.
    
    Similar to MasterCompanyRoleOccupation, this stores unique category names
    that can be referenced by SkillTaxonomy records.
    """
    __tablename__ = 'etter_master_skill_taxonomy_categories'
    __table_args__ = {'schema': 'etter'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(250), nullable=False, unique=True)


skill_taxonomy_role_association = Table(
    'etter_skill_taxonomy_role_association',
    Base.metadata,
    Column('skill_taxonomy_id', Integer, ForeignKey('etter.etter_skill_taxonomy.id', ondelete='CASCADE'), primary_key=True),
    Column('role_taxonomy_id', Integer, ForeignKey('etter.etter_role_taxonomy.id', ondelete='CASCADE'), primary_key=True),
    schema='etter'
)


class SkillTaxonomy(ApproverModel):
    """
    Stores skill taxonomy data for skills.
    
    Links to company via MasterCompany and user via User.
    Contains skill-related fields like skill_id, skill_name, category, proficiency levels, etc.
    """
    __tablename__ = 'etter_skill_taxonomy'
    __table_args__ = (
        UniqueConstraint('company_id', 'skill_name', name='uix_skill_taxonomy_company_skill_name'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(
        Integer,
        ForeignKey('iris1.iris1_mastercompany.id'),
        nullable=False
    )
    skill_id = Column(String(250), nullable=True)
    skill_name = Column(String(250), nullable=False)
    category = Column(String(250), nullable=True)
    category_id = Column(
        Integer,
        ForeignKey('etter.etter_master_skill_taxonomy_categories.id'),
        nullable=True
    )
    description = Column(Text, nullable=True)
    proficiency_levels = Column(JSONB, nullable=True)
    in_demand = Column(Boolean, nullable=False, server_default="false")
    draup_skill = Column(String(250), nullable=True)
    skill_type = Column(String(200), nullable=True)
    source = Column(String(250), nullable=False, server_default="User")
    user_id = Column(
        Integer,
        ForeignKey('etter.etter_users.id'),
        nullable=False
    )
    
    company = relationship('MasterCompany')
    user = relationship('User', foreign_keys=[user_id], backref='skill_taxonomies')
    approver = relationship('User', foreign_keys='SkillTaxonomy.approver_id', backref='approved_skill_taxonomies')
    category_master = relationship('MasterSkillTaxonomyCategories', foreign_keys=[category_id])


class MasterTechStackCategory(BaseModel):
    """
    Master table for tech stack categories.
    
    Stores unique category names that can be referenced by TechStackTaxonomy records.
    """
    __tablename__ = 'etter_master_tech_stack_category'
    __table_args__ = {'schema': 'etter'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(250), nullable=False, unique=True)


class MasterG2ProductSubSubCategory3(Base):
    """
    Master table for G2 product sub-sub category 3.
    
    Stores G2 category classifications.
    """
    __tablename__ = 'iris1_masterg2productsubsubcategory3'
    __table_args__ = {'schema': 'iris1'}

    id = Column(Integer, primary_key=True)
    g2_sub_sub_category_3 = Column(String(200), nullable=False)


class MasterTechStack(Base):
    """
    Master table referencing iris1_digitalapplicationsandplatform.
    
    Stores tech stack/product information from the digital applications platform.
    """
    __tablename__ = 'iris1_digitalapplicationsandplatform'
    __table_args__ = {'schema': 'iris1'}

    id = Column(Integer, primary_key=True)
    product_name = Column('digital_product', String(500), nullable=True)
    description = Column(Text, nullable=True)
    product_picture_s3_url = Column(String(2000), nullable=True)
    g2_main_sub_sub_category_id = Column(
        Integer,
        ForeignKey('iris1.iris1_masterg2productsubsubcategory3.id'),
        nullable=True
    )
    
    g2_category = relationship('MasterG2ProductSubSubCategory3', foreign_keys=[g2_main_sub_sub_category_id])
    
    @property
    def g2_sub_sub_category_3(self):
        """Get g2_sub_sub_category_3 from related table."""
        return self.g2_category.g2_sub_sub_category_3 if self.g2_category else None


tech_stack_taxonomy_role_association = Table(
    'etter_tech_stack_taxonomy_role_association',
    Base.metadata,
    Column('tech_stack_taxonomy_id', Integer, ForeignKey('etter.etter_tech_stack_taxonomy.id', ondelete='CASCADE'), primary_key=True),
    Column('role_taxonomy_id', Integer, ForeignKey('etter.etter_role_taxonomy.id', ondelete='CASCADE'), primary_key=True),
    schema='etter'
)


class TechStackTaxonomy(ApproverModel):
    """
    Stores tech stack taxonomy data.
    
    Links to company via MasterCompany and user via User.
    Contains tech stack-related fields like tech_stack_name, category, description, etc.
    """
    __tablename__ = 'etter_tech_stack_taxonomy'
    __table_args__ = (
        UniqueConstraint('company_id', 'tech_stack_name', name='uix_tech_stack_taxonomy_company_tech_stack_name'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(
        Integer,
        ForeignKey('iris1.iris1_mastercompany.id'),
        nullable=False
    )
    tech_stack_name = Column(String(250), nullable=False)
    description = Column(Text, nullable=True)
    image_link = Column(String(1000), nullable=True)
    category_id = Column(
        Integer,
        ForeignKey('etter.etter_master_tech_stack_category.id'),
        nullable=True
    )
    tech_stack_id = Column(
        Integer,
        ForeignKey('iris1.iris1_digitalapplicationsandplatform.id'),
        nullable=True
    )
    source = Column(String(250), nullable=False, server_default="User")
    user_id = Column(
        Integer,
        ForeignKey('etter.etter_users.id'),
        nullable=False
    )
    
    company = relationship('MasterCompany')
    user = relationship('User', foreign_keys=[user_id], backref='tech_stack_taxonomies')
    approver = relationship('User', foreign_keys='TechStackTaxonomy.approver_id', backref='approved_tech_stack_taxonomies')
    category_master = relationship('MasterTechStackCategory', foreign_keys=[category_id])
    tech_stack_master = relationship('MasterTechStack', foreign_keys=[tech_stack_id])
