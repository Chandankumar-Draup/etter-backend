from pydantic import BaseModel, Field, field_validator
from pydantic import ConfigDict
from typing import Optional, Union
from datetime import datetime


class WorkflowSteps(BaseModel):
    step_name: str
    step_info: dict = {}


class CreateNewWorkflow(BaseModel):
    workflow_name: str
    info: dict = {}
    steps: list[WorkflowSteps]


class UpsertUserWorkflowHistory(BaseModel):
    user_query: str
    workflow_name: str
    request_id: Optional[str] = None
    workflow_status: Optional[str] = "Pending"
    approval_status: Optional[str] = "Pending"
    approver_name: Optional[str] = None
    is_etter_generated: Optional[bool] = False
    score: Optional[int] = 0
    info: Optional[dict] = None
    modeling_state: Optional[str] = "INITIAL"


class UpsertUserWorkflowStepHistory(BaseModel):
    user_query: str
    workflow_name: str
    workflow_step_name: str
    request_id: str
    data_type: Optional[str] = None
    workflow_step_status: Optional[str] = "Pending"
    data: dict
    review: Optional[str] = None
    version_id: Optional[int] = 1
    update_version: Optional[bool] = False


class UserWorkflowFilters(BaseModel):
    workflow_status: Optional[str] = None
    approval_status: Optional[str] = None


class UserWorkflowStepFilters(BaseModel):
    id: Optional[int] = None
    request_id: Optional[str] = None
    workflow_name: Optional[str] = None
    user_query: Optional[str] = None
    username: Optional[int] = None
    version_id: Optional[int] = None
    fetch_all: Optional[bool] = False
    fetch_CHRO: Optional[bool] = False
    info: Optional[dict] = None
    etter_impact_score_id: Optional[int] = None
    validated_ai_impact_score_id: Optional[int] = None


class UserWorkflowHistoryFilters(BaseModel):
    workflow_name: Optional[str] = None
    step_name: Optional[str] = None
    approver_name: Optional[str] = None
    approval_status: Optional[str] = None
    workflow_status: Optional[str] = None
    user_query: Optional[str] = None
    unread_flag: Optional[bool] = None
    page: int = 0
    limit: int = 30


class ColumnFilter(BaseModel):
    column: str
    value: Union[str, int, float, bool, list[str], list[int], None]
    condition: str


class AutoCompleteFilters(BaseModel):
    flag: str
    key: str
    sort_dict: Optional[dict] = None
    getColumns: Optional[list[str]] = None
    input: Optional[str] = None
    filters: Optional[list] = []


class FetchAutocompleteDataRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    search_type: str
    search_string: Optional[str] = None
    limit: Optional[int] = 10
    title: Optional[str] = None
    company_id: Optional[int] = Field(None, alias="companyId")
    company: Optional[str] = None
    role: Optional[str] = None
    high_level_func: Optional[str] = None
    sub_level_func: Optional[str] = None


class RefreshTaskAutocompleteRequest(BaseModel):
    company: str
    role: str


class MasterCompanyData(BaseModel):
    company_name: str
    logo: str


class TableDataRequest(BaseModel):
    table_name: str
    columns_to_fetch: list[str]
    filter_column: Optional[str] = None
    filter_value: Optional[str] = None
    order_by_column: Optional[str] = None
    order_direction: str = "ASC"
    limit: int = 10

class EmployeeGroupProfile(BaseModel):
    role: str
    count: int
    salary: float

class SimulationRequest(BaseModel):
    n_iterations: int
    automation_factor: float
    roles: list[EmployeeGroupProfile]
    company: Optional[str] = ""


class RoleAdjacencyRequest(BaseModel):
    company: str
    job_role: str
    top_k: int = 8
    description: Optional[str] = None
    candidate_roles: Optional[list[str]] = None

class FetchAdjacencyRequest(BaseModel):
    company_id: int
    job_role: str
    version: Optional[str] = 'v2'

class CompanySimulationRequest(BaseModel):
    company_name: str
    max_roles: Optional[int] = None


class MasterFunctionItem(BaseModel):
    high_level_func: str
    sub_level_func: str

    @field_validator('high_level_func', 'sub_level_func')
    @classmethod
    def validate_length(cls, v):
        if v and len(v) > 200:
            raise ValueError('high_level_func and sub_level_func must not exceed 200 characters')
        return v


class MasterFunctionBulkUpsertRequest(BaseModel):
    data: list[MasterFunctionItem]


class MasterFunctionDeleteRequest(BaseModel):
    high_level_func: str
    sub_level_func: str


class FunctionCreate(BaseModel):
    high_level_func: str
    sub_level_func: str
    description: Optional[str] = None
    score: Optional[float] = None
    company_id: int

    @field_validator('high_level_func', 'sub_level_func')
    @classmethod
    def validate_length(cls, v):
        if v and len(v) > 200:
            raise ValueError('high_level_func and sub_level_func must not exceed 200 characters')
        return v


class FunctionUpdate(BaseModel):
    high_level_func: Optional[str] = None
    sub_level_func: Optional[str] = None
    description: Optional[str] = None
    score: Optional[float] = None
    company_id: Optional[int] = None

    @field_validator('high_level_func', 'sub_level_func')
    @classmethod
    def validate_length(cls, v):
        if v and len(v) > 200:
            raise ValueError('high_level_func and sub_level_func must not exceed 200 characters')
        return v


class FunctionResponse(BaseModel):
    id: int
    master_function_id: int
    high_level_func: Optional[str] = None
    sub_level_func: Optional[str] = None
    description: Optional[str] = None
    score: Optional[float] = None
    company_id: int
    created_on: datetime
    modified_on: Optional[datetime] = None


class WorkflowCreate(BaseModel):
    workflow_name: str
    description: Optional[str] = None
    score: Optional[float] = None
    approver_id: Optional[int] = None
    approval_status: Optional[str] = None
    function_id: int
    insights: Optional[dict] = None
    priority: Optional[str] = None
    frequency: Optional[str] = None
    objective: Optional[str] = None
    source: Optional[str] = "User"

    @field_validator('workflow_name')
    @classmethod
    def validate_workflow_name(cls, v):
        if v and len(v) > 200:
            raise ValueError('workflow_name must not exceed 200 characters')
        return v

    @field_validator('approval_status')
    @classmethod
    def validate_approval_status(cls, v):
        if v and len(v) > 200:
            raise ValueError('approval_status must not exceed 200 characters')
        return v


class WorkflowUpdate(BaseModel):
    workflow_name: Optional[str] = None
    description: Optional[str] = None
    score: Optional[float] = None
    approver_id: Optional[int] = None
    approval_status: Optional[str] = None
    function_id: Optional[int] = None
    insights: Optional[dict] = None
    priority: Optional[str] = None
    frequency: Optional[str] = None
    objective: Optional[str] = None
    source: Optional[str] = "User"

    @field_validator('workflow_name')
    @classmethod
    def validate_workflow_name(cls, v):
        if v and len(v) > 200:
            raise ValueError('workflow_name must not exceed 200 characters')
        return v

    @field_validator('approval_status')
    @classmethod
    def validate_approval_status(cls, v):
        if v and len(v) > 200:
            raise ValueError('approval_status must not exceed 200 characters')
        return v


class WorkflowResponse(BaseModel):
    id: int
    workflow_name: str
    description: Optional[str] = None
    score: Optional[float] = None
    researcher_id: Optional[int] = None
    approver_id: Optional[int] = None
    approval_status: Optional[str] = None
    function_id: int
    created_on: datetime
    modified_on: Optional[datetime] = None
    insights: Optional[dict] = None
    priority: Optional[str] = None
    frequency: Optional[str] = None
    objective: Optional[str] = None
    source: Optional[str] = "User"


class TaskCreate(BaseModel):
    task_name: str
    description: Optional[str] = None
    impact_score: Optional[float] = None
    roles: Optional[list[str]] = None
    skills_required: Optional[list[str]] = None
    task_type: Optional[str] = None
    position: Optional[int] = 0
    sequence_number: Optional[int] = None
    dependencies: Optional[list[int]] = None
    workflow_id: int
    automation_priority: Optional[str] = None
    score_breakdown: Optional[dict] = None

    @field_validator('task_name')
    @classmethod
    def validate_task_name(cls, v):
        if v and len(v) > 200:
            raise ValueError('task_name must not exceed 200 characters')
        return v

    @field_validator('task_type')
    @classmethod
    def validate_task_type(cls, v):
        if v and len(v) > 25:
            raise ValueError('task_type must not exceed 25 characters')
        return v


class TaskUpdate(BaseModel):
    task_name: Optional[str] = None
    description: Optional[str] = None
    impact_score: Optional[float] = None
    roles: Optional[list[str]] = None
    skills_required: Optional[list[str]] = None
    task_type: Optional[str] = None
    position: Optional[int] = None
    sequence_number: Optional[int] = None
    dependencies: Optional[list[int]] = None
    workflow_id: Optional[int] = None
    automation_priority: Optional[str] = None
    score_breakdown: Optional[dict] = None

    @field_validator('task_name')
    @classmethod
    def validate_task_name(cls, v):
        if v and len(v) > 200:
            raise ValueError('task_name must not exceed 200 characters')
        return v

    @field_validator('task_type')
    @classmethod
    def validate_task_type(cls, v):
        if v and len(v) > 25:
            raise ValueError('task_type must not exceed 25 characters')
        return v


class TaskResponse(BaseModel):
    id: int
    task_name: str
    description: Optional[str] = None
    impact_score: Optional[float] = None
    roles: Optional[list[str]] = None
    skills_required: Optional[list[str]] = None
    task_type: Optional[str] = None
    position: int
    sequence_number: Optional[int] = None
    dependencies: Optional[list[int]] = None
    workflow_id: int
    created_on: datetime
    modified_on: Optional[datetime] = None
    automation_priority: Optional[str] = None
    score_breakdown: Optional[dict] = None


class TaskPositionUpdate(BaseModel):
    id: int
    position: int


class TaskReorderRequest(BaseModel):
    tasks: list[TaskPositionUpdate]


class ComprehensiveTaskCreate(BaseModel):
    task_name: str
    description: Optional[str] = None
    roles: Optional[list[str]] = None
    skills_required: Optional[list[str]] = None
    impact_score: Optional[float] = None
    task_type: Optional[str] = None
    workload: Optional[str] = None
    automation_priority: Optional[str] = None
    score_breakdown: Optional[dict] = None
    sequence_number: Optional[int] = None
    dependencies: Optional[list[int]] = None


class ComprehensiveWorkflowCreate(BaseModel):
    workflow_name: str
    description: Optional[str] = None
    ai_optimization_score: Optional[float] = None
    insights: Optional[dict] = None
    priority: Optional[str] = None
    frequency: Optional[str] = None
    objective: Optional[str] = None
    source: Optional[str] = "User"
    tasks: list[ComprehensiveTaskCreate]


class FunctionAreaData(BaseModel):
    high_level_func: str
    sub_level_func: str
    workflows: list[ComprehensiveWorkflowCreate]


class ComprehensiveFunctionWorkflowCreate(BaseModel):
    company_name: str
    function_areas: list[FunctionAreaData]


class WorkflowBuilderProcessRequest(BaseModel):
    workflow_name: str
    company_name: str
    business_function: str
    workflow_description: Optional[str] = None
    workflow_objective: Optional[str] = None
    workflow_frequency: Optional[str] = None
    workflow_priority: Optional[str] = None
    use_llm: bool
    force_refresh: bool
    sub_level_func: Optional[str] = None
    high_level_func: Optional[str] = None


class SampleDataCreate(BaseModel):
    title: str
    is_global: Optional[bool] = False
    role: str
    data: dict
    company_id: Optional[int] = None


class CreateWorkflowFromSampleRequest(BaseModel):
    company_name: str


class SampleDataUpdate(BaseModel):
    title: Optional[str] = None
    is_global: Optional[bool] = None
    role: Optional[str] = None
    data: Optional[dict] = None
    company_id: Optional[int] = None


class SampleDataResponse(BaseModel):
    id: int
    title: str
    is_global: bool
    role: str
    data: dict
    company_id: Optional[int] = None
    updated_on: datetime


class SampleDataFilter(BaseModel):
    title: Optional[str] = None
    role: Optional[str] = None


class SampleDataBulkUpsertItem(BaseModel):
    title: str
    role: str
    is_global: Optional[bool] = False
    company_name: Optional[str] = None
    data: dict


class SampleDataBulkUpsertRequest(BaseModel):
    items: list[SampleDataBulkUpsertItem]


class SampleDataTitleCheckRequest(BaseModel):
    titles: list[str]
    company_id: Optional[int] = None


class WorkflowBuilderSampleDataBulkUpsertItem(BaseModel):
    high_level_func: str
    sub_level_func: str
    is_global: Optional[bool] = False
    data: dict


class WorkflowBuilderSampleDataBulkUpsertRequest(BaseModel):
    company_name: Optional[str] = None
    items: list[WorkflowBuilderSampleDataBulkUpsertItem]


class WorkflowBuilderSampleDataResponse(BaseModel):
    id: int
    master_function_id: int
    high_level_func: str
    sub_level_func: str
    is_global: bool
    data: dict
    company_id: Optional[int] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
    created_on: datetime
    modified_on: Optional[datetime] = None


class WorkflowBuilderSampleDataBulkUpsertResponse(BaseModel):
    status: str
    data: Optional[list[WorkflowBuilderSampleDataResponse]] = None
    errors: list[str] = []


class WorkflowBuilderSampleDataDeleteRequest(BaseModel):
    id: Optional[int] = None
    company_name: Optional[str] = None
    high_level_func: Optional[str] = None
    sub_level_func: Optional[str] = None


class WorkflowBuilderSampleDataDeleteResponse(BaseModel):
    status: str
    message: str
    deleted_count: int
    errors: list[str] = []


# Task Source API Schemas
class TaskSourceRequest(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    workflow_id: Optional[int] = None
    workflow_name: Optional[str] = None
    function_id: Optional[int] = None  # Required when using workflow_name


class TaskItem(BaseModel):
    task_name: str


class TaskSourceResponse(BaseModel):
    status: str
    source: str  # "role", "workflow", or "consolidator"
    tasks: list[str]  # Simple list of task names
    metadata: dict


class TaskSimulatorScoresRequest(BaseModel):
    tasks: list[str]
    company: Optional[str] = None
    role: Optional[str] = None


class ModelTaskResult(BaseModel):
    """Result from a single model for a task."""
    model: str
    score: int


class TaskSimulatorScoresResponse(BaseModel):
    """Response schema for task simulator scores."""
    task: str
    task_type: Optional[str] = None  # Human+AI, Human, or AI
    mean_scores: float
    variances: float
    model_task_results: list[ModelTaskResult]


class EnrichTaskItem(BaseModel):
    task_name: str
    description: Optional[str] = None
    expected_output: Optional[str] = None
    time_hours: Optional[float] = None
    complexity: Optional[str] = None
    impact_score: Optional[float] = None
    automation_type: Optional[str] = None
    skills_required: Optional[list[str]] = None
    sequence_number: Optional[int] = None
    dependencies: Optional[list[int]] = None


class EnrichTasksRequest(BaseModel):
    business_function: str
    company_name: str
    workflow_name: str
    workflow_frequency: Optional[str] = "weekly"
    use_llm: Optional[bool] = True
    tasks: list[EnrichTaskItem]
    sub_level_func: Optional[str] = None
    high_level_func: Optional[str] = None


class EditedTaskItem(BaseModel):
    task_name: str
    automation_type: Optional[str] = None
    time_hours: Optional[float] = 1.0
    complexity: Optional[str] = "moderate"
    impact_score: Optional[float] = 10.0


class RecalculateScoreRequest(BaseModel):
    business_function: str
    company_name: str
    workflow_name: str
    edited_tasks: list[EditedTaskItem]


class DynamicProxyRequest(BaseModel):
    endpoint_path: str
    payload: Optional[dict] = None
    method: Optional[str] = "POST"


class SubFunctionScoreRequest(BaseModel):
    high_level_func: str
    company_id: int


class SubFunctionScoreItem(BaseModel):
    function_id: int
    master_function_id: int
    sub_level_func: str
    description: Optional[str] = None
    function_score: Optional[float] = None
    average_workflow_score: Optional[float] = None
    workflow_count: int
    created_on: datetime
    modified_on: Optional[datetime] = None


class SubFunctionScoreResponse(BaseModel):
    status: str
    high_level_func: str
    company_id: int
    company_name: Optional[str] = None
    sub_functions: list[SubFunctionScoreItem]
    total_count: int


class EnsureFunctionRequest(BaseModel):
    high_level_func: str
    sub_level_func: str
    company_id: int
    description: Optional[str] = None
    score: Optional[float] = None

    @field_validator('high_level_func', 'sub_level_func')
    @classmethod
    def validate_length(cls, v):
        if v and len(v) > 200:
            raise ValueError('high_level_func and sub_level_func must not exceed 200 characters')
        return v


class EnsureFunctionResponse(BaseModel):
    status: str
    created: bool
    function: dict
    master_function: dict
