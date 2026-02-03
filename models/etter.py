from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, UniqueConstraint, ARRAY, Float, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from models.auth import User
from models.base_models import BaseModel
from settings.database import Base
import enum
from datetime import datetime


class ModelingState(str, enum.Enum):
    INITIAL = "INITIAL"
    IN_REVIEW = "IN_REVIEW"
    FINAL = "FINAL"


class MasterCompany(Base):
    __tablename__ = 'iris1_mastercompany'
    __table_args__ = {'schema': 'iris1'}

    id = Column(Integer, primary_key=True)
    company_name = Column(String(200))
    logo = Column(String(500), nullable=False)
    light_theme_image = Column(Text, nullable=True)
    dark_theme_image = Column(Text, nullable=True)


class WorkflowInfo(Base):
    __tablename__ = 'etter_workflowinfo'
    __table_args__ = {'schema': 'etter'}

    id = Column(Integer, primary_key=True)
    workflow_name = Column(String(200), nullable=False, unique=True)
    info = Column(JSONB, nullable=False, default={})
    
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime)
    created_by = Column(String(200), nullable=False)
    updated_by = Column(String(200))
    
    steps = relationship('WorkflowStepsInfo', back_populates='workflow')

    user_workflow_history = relationship('UserWorkflowHistory', back_populates='workflow_info')


class WorkflowStepsInfo(Base):
    __tablename__ = 'etter_workflowstepsinfo'
    __table_args__ = (
        UniqueConstraint('workflow_id', 'step_name', name='uix_workflow_step'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey('etter.etter_workflowinfo.id'), nullable=False)
    workflow = relationship('WorkflowInfo', back_populates='steps')
    step_name = Column(String(200), nullable=False)
    info = Column(JSONB, nullable=False, default={})

    user_workflow_steps_history_info = relationship('UserWorkflowStepsHistory',
                                                    back_populates='workflow_step_info')
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime)
    created_by = Column(String(200), nullable=False)
    updated_by = Column(String(200))


class UserWorkflowHistory(Base):
    __tablename__ = 'etter_userworkflowshistory'
    __table_args__ = (
        UniqueConstraint("request_id", "workflow_id", "user_id", "user_query"),
        Index('idx_etter_userworkflowshistory_user_id', 'user_id'),
        Index('idx_etter_userworkflowshistory_workflow_id', 'workflow_id'),
        Index('idx_etter_userworkflowshistory_status', 'workflow_status'),
        Index('idx_etter_userworkflowshistory_composite', 'user_id', 'workflow_id', 'workflow_status'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(200), nullable=False)
    workflow_id = Column(Integer, ForeignKey('etter.etter_workflowinfo.id'), nullable=False)
    workflow_info = relationship('WorkflowInfo', back_populates='user_workflow_history')
    user_query = Column(String(200), nullable=True)
    user_id = Column(Integer, ForeignKey('etter.etter_users.id'), nullable=False)
    user = relationship('User', foreign_keys=[user_id], back_populates='workflow_history')
    workflow_status = Column(String(200), nullable=False)
    approval_status = Column(String(200), nullable=False)

    approver_id = Column(Integer, ForeignKey('etter.etter_users.id'), nullable=True)
    approver = relationship('User', foreign_keys=[approver_id], back_populates='approver_history')

    user_workflow_steps_history = relationship('UserWorkflowStepsHistory',
                                               back_populates='user_workflow_history')
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime)
    status_records = relationship('UserWorkflowHistoryStatus', back_populates='history', cascade='all, delete-orphan')
    is_etter_generated = Column(Boolean, default=False, nullable=False)
    info = Column(JSONB, nullable=True, default=None)
    score = Column(Float)
    modeling_state = Column(Enum(ModelingState), default=ModelingState.INITIAL, nullable=False)


class UserWorkflowHistoryStatus(Base):
    __tablename__ = 'etter_userworkflowhistorystatus'
    __table_args__ = (UniqueConstraint("history_id", "user_id"), {'schema': 'etter'})

    id = Column(Integer, primary_key=True, autoincrement=True)
    history_id = Column(Integer, ForeignKey('etter.etter_userworkflowshistory.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('etter.etter_users.id'), nullable=False)
    unread_flag = Column(Boolean, default=True, nullable=False)

    history = relationship('UserWorkflowHistory', back_populates='status_records')
    user = relationship('User')

    @property
    def username(self):
        return self.user.username if self.user else None


class UserWorkflowStepsHistory(Base):
    __tablename__ = 'etter_userworkflowstephistory'
    __table_args__ = (
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(200), nullable=False)
    version_id = Column(Integer, nullable=False)
    user_workflow_history_id = Column(Integer, ForeignKey('etter.etter_userworkflowshistory.id'), nullable=False)
    user_workflow_history = relationship('UserWorkflowHistory', back_populates='user_workflow_steps_history')
    workflow_step_info_id = Column(Integer, ForeignKey('etter.etter_workflowstepsinfo.id'))
    workflow_step_info = relationship('WorkflowStepsInfo', back_populates='user_workflow_steps_history_info')
    workflow_step_status = Column(JSONB, nullable=False, default={})
    data = Column(JSONB, nullable=False, default={})
    review = Column(String(1000))
    is_latest = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime)

class FinancialSimulator(Base):
    __tablename__ = 'etter_financialsimulator'
    __table_args__ = {'schema': 'etter'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('iris1.iris1_mastercompany.id'), nullable=False)
    modified_by = Column(Integer, ForeignKey('etter.etter_users.id'), nullable=True)
    last_ran_on = Column(DateTime, nullable=False)
    simulation_data = Column(JSONB, nullable=False)

    company = relationship('MasterCompany')
    user = relationship('User')


class RoleAdjacency(Base):
    __tablename__ = 'etter_roleadjacency'
    __table_args__ = (
        UniqueConstraint('company_id', 'job_role', name='uix_company_job_role'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('iris1.iris1_mastercompany.id'), nullable=False)
    job_role = Column(String(200), nullable=False)
    adjacency_info = Column(JSONB, nullable=False)
    updated_on = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship('MasterCompany')


class MasterFunction(Base):
    __tablename__ = 'etter_masterfunction'
    __table_args__ = (
        UniqueConstraint('high_level_func', 'sub_level_func', name='uix_high_sub_level_func'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    high_level_func = Column(String(200), nullable=False)
    sub_level_func = Column(String(200), nullable=False)
    updated_by = Column(DateTime, nullable=True)

    functions = relationship('Function', back_populates='master_function')


class Function(Base):
    __tablename__ = 'etter_function'
    __table_args__ = {'schema': 'etter'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    master_function_id = Column(Integer, ForeignKey('etter.etter_masterfunction.id'), nullable=False)
    description = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    company_id = Column(Integer, ForeignKey('iris1.iris1_mastercompany.id'), nullable=False)
    created_on = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_on = Column(DateTime, nullable=True)

    company = relationship('MasterCompany')
    master_function = relationship('MasterFunction', back_populates='functions')
    workflows = relationship('FunctionWorkflow', back_populates='function', cascade='all, delete-orphan')


class FunctionWorkflow(Base):
    __tablename__ = 'etter_functionworkflow'
    __table_args__ = (
        UniqueConstraint('workflow_name', 'function_id', name='uix_workflow_function'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    researcher_id = Column(Integer, ForeignKey('etter.etter_users.id'), nullable=True)
    approver_id = Column(Integer, ForeignKey('etter.etter_users.id'), nullable=True)
    approval_status = Column(String(200), nullable=True)
    function_id = Column(Integer, ForeignKey('etter.etter_function.id'), nullable=False)
    created_on = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_on = Column(DateTime, nullable=True)
    insights = Column(JSONB, nullable=True)
    priority = Column(String(20), nullable=True)
    frequency = Column(String(30), nullable=True)
    objective = Column(Text, nullable=True)
    source = Column(String(250), nullable=False, server_default="User")

    function = relationship('Function', back_populates='workflows')
    researcher = relationship('User', foreign_keys=[researcher_id])
    approver = relationship('User', foreign_keys=[approver_id])
    tasks = relationship('WorkflowTask', back_populates='workflow', cascade='all, delete-orphan')


class WorkflowTask(Base):
    __tablename__ = 'etter_workflowtask'
    __table_args__ = (
        UniqueConstraint('task_name', 'workflow_id', name='uix_task_workflow'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    impact_score = Column(Float, nullable=True)
    roles = Column(ARRAY(String), nullable=True)
    task_type = Column(String(25), nullable=True)
    position = Column(Integer, nullable=False, default=0)
    sequence_number = Column(Integer, nullable=True)
    dependencies = Column(ARRAY(Integer), nullable=True)
    workflow_id = Column(Integer, ForeignKey('etter.etter_functionworkflow.id'), nullable=False)
    created_on = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_on = Column(DateTime, nullable=True)
    automation_priority = Column(String(20), nullable=True)
    score_breakdown = Column(JSONB, nullable=True)
    skills_required = Column(ARRAY(String), nullable=True)

    workflow = relationship('FunctionWorkflow', back_populates='tasks')


class SampleData(Base):
    __tablename__ = 'etter_sampledata'
    __table_args__ = (
        UniqueConstraint('title', 'role', 'company_id', name='uix_title_role_company'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    is_global = Column(Boolean, nullable=False, default=False)
    role = Column(String(200), nullable=False)
    data = Column(JSONB, nullable=False)
    company_id = Column(Integer, ForeignKey('iris1.iris1_mastercompany.id'), nullable=True)
    updated_on = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship('MasterCompany')


class WorkflowBuilderSampleData(BaseModel):
    __tablename__ = 'etter_workflowbuildersampledata'
    __table_args__ = (
        UniqueConstraint('master_function_id', 'company_id', name='uix_workflow_builder_master_function_company'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    master_function_id = Column(Integer, ForeignKey('etter.etter_masterfunction.id'), nullable=False)
    is_global = Column(Boolean, nullable=False, default=False)
    data = Column(JSONB, nullable=False)
    company_id = Column(Integer, ForeignKey('iris1.iris1_mastercompany.id'), nullable=True)

    company = relationship('MasterCompany')
    master_function = relationship('MasterFunction')


class MasterCompanyRoleManagementLevel(BaseModel):
    __tablename__ = 'etter_master_company_role_management_level'
    __table_args__ = {'schema': 'etter'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(250), nullable=False, unique=True)


class MasterCompanyRoleJobTrack(BaseModel):
    __tablename__ = 'etter_master_company_role_job_track'
    __table_args__ = {'schema': 'etter'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(250), nullable=False, unique=True)


class MasterCompanyRoleJobFamily(BaseModel):
    __tablename__ = 'etter_master_company_role_job_family'
    __table_args__ = {'schema': 'etter'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(250), nullable=False, unique=True)


class MasterCompanyRoleOccupation(BaseModel):
    __tablename__ = 'etter_master_company_role_occupation'
    __table_args__ = {'schema': 'etter'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(250), nullable=False, unique=True)


class TaskFeasibility(Base):
    __tablename__ = 'etter_taskfeasibility'
    __table_args__ = (
        UniqueConstraint('company_id', 'user_query', 'task_name', name='uix_task_feasibility_company_userquery_task'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('iris1.iris1_mastercompany.id'), nullable=False)
    user_query = Column(String(200), nullable=True)
    task_name = Column(Text, nullable=False)
    task_type = Column(String(50), nullable=True)
    etter_score = Column(Float, nullable=True)
    model_score = Column(JSONB, nullable=True)
    median = Column(JSONB, nullable=True)
    updated_on = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship('MasterCompany')


class TaskAutocompleteCache(Base):
    __tablename__ = 'etter_task_autocomplete_cache'
    __table_args__ = (
        UniqueConstraint('task_name', 'company', 'role', name='uix_task_company_role'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String(500), nullable=False)
    company = Column(String(200), nullable=False)
    role = Column(String(200), nullable=False)
    task_type = Column(String(50), nullable=True)
    source = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Survey(Base):
    """
    Stores survey metadata for skill validation surveys.
    """
    __tablename__ = 'etter_survey'
    __table_args__ = {'schema': 'etter'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    company_id = Column(Integer, ForeignKey('iris1.iris1_mastercompany.id'), nullable=False)
    created_by = Column(Integer, ForeignKey('etter.etter_users.id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)

    company = relationship('MasterCompany')
    creator = relationship('User', foreign_keys=[created_by], backref='created_surveys')
    skills = relationship('SurveySkill', back_populates='survey', cascade='all, delete-orphan')
    responses = relationship('SurveyResponse', back_populates='survey', cascade='all, delete-orphan')


class SurveySkill(Base):
    """
    Links surveys to skills from SkillTaxonomy.
    """
    __tablename__ = 'etter_survey_skill'
    __table_args__ = (
        UniqueConstraint('survey_id', 'skill_id', name='uix_survey_skill'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    survey_id = Column(Integer, ForeignKey('etter.etter_survey.id'), nullable=False)
    skill_id = Column(Integer, ForeignKey('etter.etter_skill_taxonomy.id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    survey = relationship('Survey', back_populates='skills')
    # Using string reference to avoid circular import
    skill = relationship('SkillTaxonomy', foreign_keys=[skill_id], lazy='joined')


class SurveyResponse(Base):
    """
    Stores individual user responses to surveys.
    """
    __tablename__ = 'etter_survey_response'
    __table_args__ = (
        UniqueConstraint('survey_id', 'user_id', name='uix_survey_user_response'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    survey_id = Column(Integer, ForeignKey('etter.etter_survey.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('etter.etter_users.id'), nullable=False)
    feedback_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    survey = relationship('Survey', back_populates='responses')
    user = relationship('User', foreign_keys=[user_id], backref='survey_responses')
    skill_responses = relationship('SurveySkillResponse', back_populates='survey_response', cascade='all, delete-orphan')


class SurveySkillResponse(Base):
    """
    Stores individual skill responses (valid/not valid) within a survey response.
    """
    __tablename__ = 'etter_survey_skill_response'
    __table_args__ = (
        UniqueConstraint('survey_response_id', 'skill_id', name='uix_survey_response_skill'),
        {'schema': 'etter'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    survey_response_id = Column(Integer, ForeignKey('etter.etter_survey_response.id'), nullable=False)
    skill_id = Column(Integer, ForeignKey('etter.etter_skill_taxonomy.id'), nullable=False)
    is_valid = Column(Boolean, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    survey_response = relationship('SurveyResponse', back_populates='skill_responses')
    # Using string reference to avoid circular import
    skill = relationship('SkillTaxonomy', foreign_keys=[skill_id], lazy='joined')
