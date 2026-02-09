"""
Input models for Etter Workflows.

These models define the data structures for workflow and activity inputs,
following the self-similar interface contract defined in the implementation plan.

Interface Contract:
    INPUT:
    {
        "id": "unique-identifier",
        "inputs": { ... },
        "context": { "company_id": "...", "user_id": "...", "trace_id": "..." }
    }
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class DocumentType(str, Enum):
    """Types of documents that can be linked to a role."""
    JOB_DESCRIPTION = "job_description"
    PROCESS_MAP = "process_map"
    SOP = "sop"
    OTHER = "other"


class DocumentRef(BaseModel):
    """
    Reference to a document for role processing.

    Attributes:
        type: Type of document (job_description, process_map, etc.)
        uri: URI to the document (s3://, file://, or content string)
        name: Optional human-readable name
        content: Optional inline content (for direct passing)
        metadata: Optional additional metadata
    """
    type: DocumentType
    uri: Optional[str] = None
    name: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def has_content(self) -> bool:
        """Check if document has content (either inline or via URI)."""
        return bool(self.content) or bool(self.uri)


class ExecutionContext(BaseModel):
    """
    Context information for workflow execution.

    This context is passed through all activities and workflows
    for tracing, authorization, and audit purposes.

    Attributes:
        company_id: Company identifier
        user_id: User who triggered the workflow
        trace_id: Unique trace ID for distributed tracing
        session_id: Optional session ID for grouping operations
        created_at: Timestamp when context was created
    """
    company_id: str
    user_id: str
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "company_id": self.company_id,
            "user_id": self.user_id,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
        }


class WorkflowOptions(BaseModel):
    """
    Options for workflow execution.

    Attributes:
        skip_enhancement_workflows: Skip Skills Architecture, Task Feasibility, etc.
        force_rerun: Force re-run even if results exist
        notify_on_complete: Send notification when complete
        timeout_minutes: Custom timeout for the workflow
        priority: Priority level (higher = more urgent)
    """
    skip_enhancement_workflows: bool = False
    force_rerun: bool = False
    notify_on_complete: bool = True
    timeout_minutes: int = 120
    priority: int = 5  # 1-10, default 5


class RoleTaxonomyEntry(BaseModel):
    """
    Role taxonomy entry from the platform.

    This represents the input format from the role taxonomy API.
    Based on push_to_platform.py format.

    Attributes:
        job_id: Unique job identifier
        job_role: Draup role name
        job_title: Original job title from company
        occupation: Occupation category
        job_family: Job family category
        job_level: Job level (if available)
        job_track: Job track (if available)
        management_level: Management level
        pay_grade: Pay grade (if available)
        draup_role: Draup standardized role
        general_summary: Job description summary
        duties_responsibilities: Duties and responsibilities text
        work_experience: Required work experience
        source: Source of the role data
        is_active: Whether the role is active
        status: Status of the role (pending, approved, rejected)
    """
    job_id: str
    job_role: str
    job_title: str
    occupation: Optional[str] = None
    job_family: Optional[str] = None
    job_level: Optional[str] = None
    job_track: Optional[str] = None
    management_level: Optional[str] = None
    pay_grade: Optional[str] = None
    draup_role: Optional[str] = None
    general_summary: Optional[str] = None
    duties_responsibilities: Optional[str] = None
    work_experience: Optional[str] = None
    source: str = "etter"
    is_active: bool = True
    status: str = "pending"

    def get_draup_role(self) -> str:
        """Get the Draup role, falling back to job_role if not set."""
        return self.draup_role or self.job_role

    def has_job_description(self) -> bool:
        """Check if the entry has job description content."""
        return bool(self.general_summary or self.duties_responsibilities)


class RoleOnboardingInput(BaseModel):
    """
    Input for the role onboarding workflow.

    This is the main input model for the self-service pipeline.
    It follows the self-similar interface contract.

    Attributes:
        id: Unique identifier for this request
        company_id: Company identifier (e.g., "liberty-mutual")
        role_name: Role name to onboard
        documents: List of documents to link
        draup_role_id: Optional Draup role mapping
        taxonomy_entry: Optional full taxonomy entry
        options: Workflow execution options
        context: Execution context
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    role_name: str
    documents: List[DocumentRef] = Field(default_factory=list)
    draup_role_id: Optional[str] = None
    draup_role_name: Optional[str] = None
    taxonomy_entry: Optional[RoleTaxonomyEntry] = None
    options: WorkflowOptions = Field(default_factory=WorkflowOptions)
    context: Optional[ExecutionContext] = None

    def __init__(self, **data):
        super().__init__(**data)
        # Auto-create context if not provided
        if self.context is None:
            self.context = ExecutionContext(
                company_id=self.company_id,
                user_id="system",
            )

    def has_documents(self) -> bool:
        """Check if at least one document is linked."""
        return len(self.documents) > 0 and any(d.has_content() for d in self.documents)

    def get_job_description(self) -> Optional[DocumentRef]:
        """Get the job description document if available.

        Handles both DocumentRef objects and dicts (after Temporal serialization).
        """
        for doc in self.documents:
            try:
                # Handle dict case (after Temporal deserialization)
                if isinstance(doc, dict):
                    doc_type = doc.get("type", "")
                    type_lower = str(doc_type).lower() if doc_type else ""
                    if "job_description" in type_lower:
                        # Convert dict back to DocumentRef
                        return DocumentRef(**doc)
                else:
                    # Handle DocumentRef object case
                    doc_type = getattr(doc, 'type', None)
                    if doc_type is None:
                        continue
                    # Compare as strings to handle both enum and string cases
                    type_str = doc_type.value if hasattr(doc_type, 'value') else str(doc_type)
                    if "job_description" in type_str.lower():
                        return doc
            except Exception:
                # Skip any malformed document entries
                continue
        return None

    def get_process_maps(self) -> List[DocumentRef]:
        """Get all process map documents."""
        return [d for d in self.documents if d.type == DocumentType.PROCESS_MAP]

    def validate_for_processing(self) -> List[str]:
        """
        Validate that the input is ready for processing.

        Only company_id and role_name are required. Documents are optional -
        the workflow will still call create_company_role without them.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.company_id:
            errors.append("company_id is required")

        if not self.role_name:
            errors.append("role_name is required")

        return errors


class BatchInput(BaseModel):
    """
    Input for batch processing multiple roles.

    Attributes:
        id: Unique identifier for this batch
        roles: List of role onboarding inputs
        context: Shared execution context
        options: Shared workflow options (can be overridden per role)
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    roles: List[RoleOnboardingInput]
    context: Optional[ExecutionContext] = None
    options: WorkflowOptions = Field(default_factory=WorkflowOptions)

    def get_valid_roles(self) -> List[RoleOnboardingInput]:
        """Get roles that pass validation."""
        return [r for r in self.roles if not r.validate_for_processing()]

    def get_invalid_roles(self) -> List[tuple]:
        """Get roles that fail validation with their errors."""
        return [
            (r, r.validate_for_processing())
            for r in self.roles
            if r.validate_for_processing()
        ]
