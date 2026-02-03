from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from uuid import UUID

from models.extraction import ApprovalStatus, ExtractionSessionStatus


class CreateSessionRequest(BaseModel):
    """Request to create a new extraction session."""
    pass


class CreateSessionResponse(BaseModel):
    """Response after creating a session."""
    session_id: str
    status: str
    user_name: Optional[str]
    created_at: datetime


class ProcessDocumentRequest(BaseModel):
    """Request to process one or more documents for extraction."""
    session_id: UUID = Field(..., description="Extraction session ID")
    document_ids: List[UUID] = Field(
        ...,
        description="List of S3 document IDs to process (1-5 documents)",
        min_length=1,
        max_length=5
    )


class DocumentRecordInfo(BaseModel):
    """Information about a created extraction record."""
    document_id: str
    record_id: int
    status: str
    error: Optional[str] = None


class ProcessDocumentResponse(BaseModel):
    """Response after initiating document processing."""
    session_id: str
    total_documents: int
    records: List[DocumentRecordInfo]
    message: str


class ExtractedDocumentResponse(BaseModel):
    """Response model for extracted document details."""
    id: int
    document_id: str
    document_name: Optional[str]
    status: str
    document_type: Optional[str]
    extraction_confidence: Optional[int]
    tasks: Optional[list]
    skills: Optional[list]
    stages: Optional[list]
    roles: Optional[list]
    approval_status: str
    error_message: Optional[str]
    created_on: datetime
    modified_on: Optional[datetime]

    class Config:
        from_attributes = True


class SessionStatusResponse(BaseModel):
    """Response for session status with all documents."""
    session_id: str
    status: str
    user_name: Optional[str]
    approver_name: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    documents: List[ExtractedDocumentResponse]
    can_complete: bool
    statistics: dict


class ApprovalRequest(BaseModel):
    """Request to approve/reject an extracted document."""
    approval_status: ApprovalStatus = Field(..., description="APPROVED or REJECTED")


class ApprovalResponse(BaseModel):
    """Response after approval action."""
    record_id: int
    approval_status: str
    approved_at: Optional[datetime]
    message: str


class SessionApprovalResponse(BaseModel):
    """Response after session approval action."""
    session_id: str
    total_documents: int
    approval_status: str
    user_name: Optional[str]
    approver_name: Optional[str]
    approved_at: Optional[datetime]
    message: str


class CompleteSessionResponse(BaseModel):
    """Response after completing a session."""
    session_id: str
    status: str
    user_name: Optional[str]
    approver_name: Optional[str]
    completed_at: datetime
    total_documents: int
    completed_count: int
    failed_count: int
    message: str


class CompanyFileResponse(BaseModel):
    """Response model for company file listing."""
    id: Optional[int]
    document_id: str
    original_filename: Optional[str]
    document_status: str
    content_type: Optional[str]
    size_bytes: Optional[int]
    created_at: datetime
    folder_path: Optional[str]
    has_extraction: bool
    extraction_status: Optional[str]
    approval_status: Optional[str]
    document_type: Optional[str]
    last_modified_at: Optional[str]


class CompanyFilesListResponse(BaseModel):
    """Response for listing all company files."""
    tenant_id: str
    total_count: int
    files: List[CompanyFileResponse]
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


class CompanyFilesFilterParams(BaseModel):
    """Filter parameters for listing company files."""
    company_instance_name: Optional[str] = None
    document_type: Optional[str] = None
    content_type: Optional[str] = None
    roles: Optional[str] = None
    status: Optional[str] = None
    
    class Config:
        from_attributes = True


class DocumentDataResponse(BaseModel):
    """Response model for document extraction data."""
    document_id: str
    document_name: Optional[str]
    status: str
    document_type: Optional[str]
    extraction_confidence: Optional[int]
    tasks: Optional[list]
    skills: Optional[list]
    stages: Optional[list]
    task_to_skill: Optional[list]
    roles: Optional[list]
    approval_status: str
    created_on: datetime
    modified_on: Optional[datetime]


class UpdateDocumentDataRequest(BaseModel):
    """Request model for updating document extraction data."""
    document_name: Optional[str] = None
    document_type: Optional[str] = None
    extraction_confidence: Optional[int] = None
    tasks: Optional[list] = None
    skills: Optional[list] = None
    stages: Optional[list] = None
    task_to_skill: Optional[list] = None
    roles: Optional[list] = None
    approval_status: Optional[ApprovalStatus] = None


class UpdateSessionRequest(BaseModel):
    """Request model for updating extraction session."""
    status: Optional[ExtractionSessionStatus] = None
    approver_username: Optional[str] = Field(None, description="Username of the approver")


class UpdateSessionResponse(BaseModel):
    """Response model for updating extraction session."""
    session_id: str
    status: str
    user_name: Optional[str]
    approver_name: Optional[str]
    approver_id: Optional[int]
    updated_at: datetime
    message: str


class RoleTaxonomyResponse(BaseModel):
    """Response model for role taxonomy data."""
    id: int
    company_id: int
    job_id: Optional[str]
    job_role: Optional[str]
    job_title: str
    occupation: str
    job_family: str
    job_level: Optional[str]
    job_track: Optional[str]
    management_level: Optional[str]
    pay_grade: Optional[str]
    draup_role: Optional[str]
    job_description: Optional[str]
    general_summary: Optional[str]
    duties_responsibilities: Optional[str]
    work_experience: Optional[str]
    skills: Optional[List[str]]
    others: Optional[dict]
    source: str
    status: str
    approver_username: Optional[str]
    user_username: Optional[str]
    modified_by_username: Optional[str]
    created_on: datetime
    updated_on: Optional[datetime]

    class Config:
        from_attributes = True


class RoleTaxonomyBulkUpsertItem(BaseModel):
    """Item for bulk upsert of role taxonomy."""
    id: Optional[int] = None
    job_id: Optional[str] = ""
    job_role: Optional[str] = ""
    job_title: str
    occupation: str
    job_family: str
    job_level: Optional[str] = ""
    job_track: Optional[str] = None
    management_level: Optional[str] = None
    pay_grade: Optional[str] = None
    draup_role: Optional[str] = None
    job_description: Optional[str] = ""
    general_summary: Optional[str] = ""
    duties_responsibilities: Optional[str] = ""
    work_experience: Optional[str] = ""
    skills: Optional[List[str]] = []
    others: Optional[dict] = None
    source: Optional[str] = "User"
    status: Optional[str] = "pending"
    user_username: Optional[str] = None
    approver_username: Optional[str] = None
    modified_by_username: Optional[str] = None


class RoleTaxonomyBulkUpsertRequest(BaseModel):
    """Request for bulk upsert of role taxonomy."""
    items: List[RoleTaxonomyBulkUpsertItem]
    force_update: bool = False
    force_upload: bool = False
    company_name: Optional[str] = None


class RoleTaxonomyBulkUpsertResponse(BaseModel):
    """Response for bulk upsert of role taxonomy."""
    status: str
    data: List[RoleTaxonomyResponse]
    total_count: int
    created_count: int
    updated_count: int
    errors: List[str]


class RoleTaxonomyBulkApproveRequest(BaseModel):
    """Request for bulk approve role taxonomy."""
    ids: List[int]
    status: Optional[str] = "approved"


class RoleTaxonomyBulkApproveResponse(BaseModel):
    """Response for bulk approve role taxonomy."""
    status: str
    approved_count: int
    errors: List[str]
    message: str


class RoleTaxonomyDeleteResponse(BaseModel):
    """Response for delete role taxonomy."""
    status: str
    message: str
    deleted_id: int


class RoleTaxonomyBulkDeleteRequest(BaseModel):
    ids: List[int]


class RoleTaxonomyBulkDeleteResponse(BaseModel):
    status: str
    deleted_count: int
    errors: List[str]
    message: str


class RoleTaxonomyListResponse(BaseModel):
    """Response model for role taxonomy list."""
    data: List[RoleTaxonomyResponse]
    total_count: int
    pending_count: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


class GroupedRoleTaxonomyListResponse(BaseModel):
    """Response model for role taxonomy list grouped by job family."""
    data: Dict[str, List[RoleTaxonomyResponse]]
    total_count: int
    pending_count: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


class SkillTaxonomyResponse(BaseModel):
    """Response model for skill taxonomy data."""
    id: int
    company_id: int
    skill_id: Optional[str]
    skill_name: str
    category: Optional[str]
    description: Optional[str]
    proficiency_levels: Optional[dict]
    in_demand: Optional[bool]
    status: str
    draup_skill: Optional[str]
    skill_type: Optional[str]
    source: str
    approver_username: Optional[str]
    user_username: Optional[str]
    modified_by_username: Optional[str]
    approved_on: Optional[datetime]
    modified_on: datetime
    created_on: datetime
    job_titles: Optional[List[str]] = []

    class Config:
        from_attributes = True


class SkillTaxonomyBulkUpsertItem(BaseModel):
    """Item for bulk upsert of skill taxonomy."""
    id: Optional[int] = None
    skill_id: Optional[str] = None
    skill_name: str
    category: Optional[str] = None
    description: Optional[str] = None
    proficiency_levels: Optional[dict] = None
    in_demand: Optional[bool] = False
    status: Optional[str] = "pending"
    draup_skill: Optional[str] = None
    skill_type: Optional[str] = None
    source: Optional[str] = "User"
    user_username: Optional[str] = None
    approver_username: Optional[str] = None
    modified_by_username: Optional[str] = None
    job_titles: Optional[List[str]] = None


class SkillTaxonomyBulkUpsertRequest(BaseModel):
    """Request for bulk upsert of skill taxonomy."""
    items: List[SkillTaxonomyBulkUpsertItem]
    force_update: bool = False
    force_upload: bool = False
    company_name: Optional[str] = None


class SkillTaxonomyBulkUpsertResponse(BaseModel):
    """Response for bulk upsert of skill taxonomy."""
    status: str
    data: List[SkillTaxonomyResponse]
    total_count: int
    created_count: int
    updated_count: int
    errors: List[str]


class SkillTaxonomyBulkApproveRequest(BaseModel):
    """Request for bulk approve skill taxonomy."""
    ids: List[int]
    status: Optional[str] = "approved"


class SkillTaxonomyBulkApproveResponse(BaseModel):
    """Response for bulk approve skill taxonomy."""
    status: str
    approved_count: int
    errors: List[str]
    message: str


class SkillTaxonomyDeleteResponse(BaseModel):
    """Response for delete skill taxonomy."""
    status: str
    message: str
    deleted_id: int


class SkillTaxonomyBulkDeleteRequest(BaseModel):
    ids: List[int]


class SkillTaxonomyBulkDeleteResponse(BaseModel):
    status: str
    deleted_count: int
    errors: List[str]
    message: str


class SkillTaxonomyListResponse(BaseModel):
    """Response model for skill taxonomy list."""
    data: List[SkillTaxonomyResponse]
    total_count: int
    pending_count: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


class GroupedSkillTaxonomyListResponse(BaseModel):
    """Response model for skill taxonomy list grouped by category."""
    data: Dict[str, List[SkillTaxonomyResponse]]
    total_count: int
    pending_count: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


class ExtractedDocumentBulkApproveRequest(BaseModel):
    """Request for bulk approve extracted documents."""
    ids: List[int]
    status: Optional[str] = "approved"


class ExtractedDocumentBulkApproveResponse(BaseModel):
    """Response for bulk approve extracted documents."""
    status: str
    approved_count: int
    errors: List[str]
    message: str


class ExtractedDocumentBulkDeleteRequest(BaseModel):
    """Request for bulk delete extracted documents."""
    ids: List[int]


class ExtractedDocumentBulkDeleteResponse(BaseModel):
    """Response for bulk delete extracted documents."""
    status: str
    deleted_count: int
    errors: List[str]
    message: str


class TechStackTaxonomyResponse(BaseModel):
    """Response model for tech stack taxonomy data."""
    id: int
    company_id: int
    tech_stack_name: str
    description: Optional[str] = None
    image_link: Optional[str] = None
    category: Optional[str] = None
    tech_stack_product_name: Optional[str] = None
    source: str
    status: Optional[str] = None
    approver_username: Optional[str] = None
    user_username: Optional[str] = None
    modified_by_username: Optional[str] = None
    modified_on: Optional[datetime] = None
    created_on: Optional[datetime] = None
    job_titles: Optional[List[str]] = []

    class Config:
        from_attributes = True


class TechStackTaxonomyBulkUpsertItem(BaseModel):
    """Item for bulk upsert of tech stack taxonomy."""
    id: Optional[int] = None
    tech_stack_name: str
    description: Optional[str] = None
    image_link: Optional[str] = None
    category: Optional[str] = None
    tech_stack_id: Optional[int] = None
    source: Optional[str] = "User"
    status: Optional[str] = "pending"
    user_username: Optional[str] = None
    approver_username: Optional[str] = None
    modified_by_username: Optional[str] = None
    job_titles: Optional[List[str]] = None


class TechStackTaxonomyBulkUpsertRequest(BaseModel):
    """Request for bulk upsert of tech stack taxonomy."""
    items: List[TechStackTaxonomyBulkUpsertItem]
    force_update: bool = False
    force_upload: bool = False
    company_name: Optional[str] = None


class TechStackTaxonomyBulkUpsertResponse(BaseModel):
    """Response for bulk upsert of tech stack taxonomy."""
    status: str
    data: List[TechStackTaxonomyResponse]
    total_count: int
    created_count: int
    updated_count: int
    errors: List[str]


class TechStackTaxonomyBulkApproveRequest(BaseModel):
    """Request for bulk approve tech stack taxonomy."""
    ids: List[int]
    status: Optional[str] = "approved"


class TechStackTaxonomyBulkApproveResponse(BaseModel):
    """Response for bulk approve tech stack taxonomy."""
    status: str
    approved_count: int
    errors: List[str]
    message: str


class TechStackTaxonomyDeleteResponse(BaseModel):
    """Response for delete tech stack taxonomy."""
    status: str
    message: str
    deleted_id: int


class TechStackTaxonomyBulkDeleteRequest(BaseModel):
    ids: List[int]


class TechStackTaxonomyBulkDeleteResponse(BaseModel):
    status: str
    deleted_count: int
    errors: List[str]
    message: str


class TechStackTaxonomyListResponse(BaseModel):
    """Response model for tech stack taxonomy list."""
    data: List[TechStackTaxonomyResponse]
    total_count: int
    pending_count: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


# =============================================================================
# Taxonomy Extraction Schemas (LLM-based column mapping)
# =============================================================================

from enum import Enum

class TaxonomyTypeEnum(str, Enum):
    """Supported taxonomy types for extraction."""
    ROLE = "role"
    SKILL = "skill"
    TECH_STACK = "tech_stack"


class TaxonomyExtractionRequest(BaseModel):
    """Request for LLM-based taxonomy extraction from a document."""
    document_id: UUID = Field(
        ...,
        description="S3 document ID (UUID) of the uploaded Excel/CSV file"
    )
    taxonomy_type: TaxonomyTypeEnum = Field(
        ...,
        description="Target taxonomy type: role, skill, or tech_stack"
    )
    user_mapping: Optional[Dict[str, str]] = Field(
        None,
        description="Optional user-provided column->field mappings to override LLM inference"
    )
    company_id: Optional[int] = Field(
        None,
        description="Company ID for database conflict detection and upsert"
    )
    preview_only: bool = Field(
        True,
        description="If true, only return mapping and validation without upserting"
    )
    sheet_name: Optional[str] = Field(
        None,
        description="Sheet name for Excel files (optional, uses first sheet by default)"
    )


class ColumnMappingResult(BaseModel):
    """Result of LLM-inferred column mappings."""
    column_mappings: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of document columns to taxonomy fields"
    )
    unmapped_columns: List[str] = Field(
        default_factory=list,
        description="Columns that could not be mapped to any taxonomy field"
    )
    required_fields_missing: List[str] = Field(
        default_factory=list,
        description="Required taxonomy fields that have no document column mapped"
    )
    confidence: float = Field(
        default=0.0,
        description="Overall mapping confidence (0.0-1.0)"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Mapping-related warnings"
    )


class DuplicateRecord(BaseModel):
    """Details about a duplicate record."""
    row_indices: List[int] = Field(
        description="Row indices in the document that are duplicates"
    )
    key_values: Dict[str, str] = Field(
        description="Key field values that identify this duplicate"
    )
    resolution: str = Field(
        default="first",
        description="How the duplicate was resolved: first, skip, etc."
    )


class ConflictRecord(BaseModel):
    """Details about a conflict with existing database record."""
    row_index: int = Field(
        description="Row index in the document"
    )
    key_values: Dict[str, str] = Field(
        description="Key field values that conflict"
    )
    existing_id: Optional[int] = Field(
        None,
        description="ID of the existing database record"
    )


class ValidationError(BaseModel):
    """Details about a validation error."""
    row_index: int = Field(
        description="Row index in the document"
    )
    field: str = Field(
        description="Field name with the error"
    )
    error: str = Field(
        description="Error message"
    )
    severity: str = Field(
        default="error",
        description="Severity: error, warning"
    )


class ValidationResult(BaseModel):
    """Validation results for extracted data."""
    total_rows: int = Field(
        default=0,
        description="Total rows processed"
    )
    valid_rows: int = Field(
        default=0,
        description="Number of valid rows"
    )
    duplicates_in_document: List[DuplicateRecord] = Field(
        default_factory=list,
        description="Duplicate records found within the document"
    )
    conflicts_with_database: List[ConflictRecord] = Field(
        default_factory=list,
        description="Conflicts with existing database records"
    )
    validation_errors: List[ValidationError] = Field(
        default_factory=list,
        description="Field-level validation errors"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="General validation warnings"
    )


class TaxonomyExtractionResponse(BaseModel):
    """Response from taxonomy extraction."""
    status: str = Field(
        description="Status: success or error"
    )
    taxonomy_type: str = Field(
        description="The taxonomy type processed"
    )
    mapping: ColumnMappingResult = Field(
        description="LLM-inferred column mappings"
    )
    validation: Optional[ValidationResult] = Field(
        None,
        description="Validation results if all_rows were provided"
    )
    transformed_data: Optional[List[Dict]] = Field(
        None,
        description="Transformed data ready for upsert (if preview_only is true)"
    )
    upsert_result: Optional[Dict] = Field(
        None,
        description="Upsert results (if not preview_only)"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if status is error"
    )
    execution_time: Optional[float] = Field(
        None,
        description="Execution time in seconds"
    )
