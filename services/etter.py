import copy
import requests
import logging

from settings.database import get_db
from datetime import datetime
from models.auth import User
from models.etter import (WorkflowInfo, WorkflowStepsInfo, UserWorkflowHistory, UserWorkflowStepsHistory,
                          UserWorkflowHistoryStatus, ModelingState, SampleData, WorkflowTask,
                          FunctionWorkflow, WorkflowBuilderSampleData)
from sqlalchemy.orm.attributes import flag_modified
import json
from sqlalchemy.orm import Session
from sqlalchemy import text, or_
from typing import List, Dict, Any, Optional
from models.etter import MasterCompany, MasterFunction, FunctionWorkflow
from sqlalchemy import func

logger = logging.getLogger(__name__)


def fetchTableData(
    db: Session,
    model_class,
    columns_to_fetch: List[str],
    filter_column: Optional[str] = None,
    filter_value: Optional[str] = None,
    order_by_column: Optional[str] = None,
    order_direction: str = "ASC",
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Reusable function to fetch data from any table using raw SQL
    
    Args:
        db: Database session
        model_class: SQLAlchemy model class (e.g., MasterCompany)
        columns_to_fetch: List of column names to fetch
        filter_column: Column name to apply LIKE filter on (optional)
        filter_value: Value to filter by (optional)
        order_by_column: Column name to order by (optional)
        order_direction: Order direction (ASC/DESC)
        limit: Number of results to return
    
    Returns:
        List of dictionaries containing the fetched data
    """
    table_name = model_class.__tablename__
    schema = model_class.__table_args__[0]['schema'] if model_class.__table_args__ else None
    
    full_table_name = f"{schema}.{table_name}" if schema else table_name
    
    if not columns_to_fetch:
        raise ValueError("At least one column must be specified")
    
    columns_str = ", ".join(columns_to_fetch)
    
    query = f"SELECT {columns_str} FROM {full_table_name}"
    params = {}
    
    if filter_column and filter_value:
        if filter_column not in columns_to_fetch:
            raise ValueError(f"Filter column '{filter_column}' must be in the selected columns")
        query += f" WHERE {filter_column} ILIKE :filter_value"
        params['filter_value'] = f"%{filter_value}%"
    
    if order_by_column:
        if order_by_column not in columns_to_fetch:
            raise ValueError(f"Order by column '{order_by_column}' must be in the selected columns")
        query += f" ORDER BY LENGTH({order_by_column}) {order_direction}"
    
    query += f" LIMIT {limit}"
    
    result = db.execute(text(query), params)
    
    return [dict(row._mapping) for row in result]


def fetchMasterCompanyData(
    db: Session,
    search_string: Optional[str] = None,
    search_company_name_only: bool = False,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Specific function to fetch company_name and logo from MasterCompany table
    
    Args:
        db: Database session
        search_string: Optional string to filter by
        search_company_name_only: If True, search only in company_name column
        limit: Number of results to return (default 10)
    
    Returns:
        List of dictionaries containing company_name and logo
    """
    columns_to_fetch = ["company_name", "logo"]
    
    if search_string:
        if search_company_name_only:
            query = """
            SELECT company_name, logo 
            FROM iris1.iris1_mastercompany 
            WHERE company_name ILIKE :search_value
            ORDER BY LENGTH(company_name) ASC
            LIMIT :limit
            """
        else:
            query = """
            SELECT company_name, logo 
            FROM iris1.iris1_mastercompany 
            WHERE company_name ILIKE :search_value
            ORDER BY LENGTH(company_name) ASC
            LIMIT :limit
            """
        result = db.execute(text(query), {
            'search_value': f"%{search_string}%",
            'limit': limit
        })
    else:
        query = """
        SELECT company_name, logo 
        FROM iris1.iris1_mastercompany 
        ORDER BY LENGTH(company_name) ASC
        LIMIT :limit
        """
        result = db.execute(text(query), {'limit': limit})
    
    return [dict(row._mapping) for row in result]


def fetchMasterFunctionData(
    db: Session,
    search_string: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Specific function to fetch high_level_func and sub_level_func from etter_masterfunction table
    
    Args:
        db: Database session
        search_string: Optional string to filter by high_level_func or sub_level_func
        limit: Number of results to return (default 10)
    
    Returns:
        List of dictionaries containing high_level_func and sub_level_func
    """
    if search_string:
        query = """
        SELECT high_level_func, sub_level_func 
        FROM etter.etter_masterfunction 
        WHERE high_level_func ILIKE :search_value OR sub_level_func ILIKE :search_value
        ORDER BY LENGTH(high_level_func) ASC, LENGTH(sub_level_func) ASC
        LIMIT :limit
        """
        result = db.execute(text(query), {
            'search_value': f"%{search_string}%",
            'limit': limit
        })
    else:
        query = """
        SELECT high_level_func, sub_level_func 
        FROM etter.etter_masterfunction 
        ORDER BY LENGTH(high_level_func) ASC, LENGTH(sub_level_func) ASC
        LIMIT :limit
        """
        result = db.execute(text(query), {'limit': limit})
    
    return [dict(row._mapping) for row in result]


def upsert_workflow_info(workflow_info_data, db=None):
    if not db:
        db = get_db()
    existing_workflow = db.query(WorkflowInfo).filter(
        WorkflowInfo.workflow_name == workflow_info_data["workflow_name"]).first()
    if existing_workflow:
        workflow_info_query_obj = existing_workflow
        workflow_info_query_obj.info = workflow_info_data["info"]
        workflow_info_query_obj.updated_by = workflow_info_data["email"]
        workflow_info_query_obj.updated_at = datetime.now()

    else:
        workflow_info_query_obj = WorkflowInfo(
            workflow_name=workflow_info_data["workflow_name"],
            info=workflow_info_data["info"],
            created_by=workflow_info_data["email"],
            created_at=datetime.now(),
        )
    db.add(workflow_info_query_obj)
    db.commit()
    db.refresh(workflow_info_query_obj)
    return workflow_info_query_obj


def upsert_workflow_step(workflow_id, username, workflow_steps, db=None):
    if not db:
        db = get_db()

    errors = []
    step_data_list = []
    for step in workflow_steps:
        try:
            workflow_step_obj = db.query(WorkflowStepsInfo).filter(
                WorkflowStepsInfo.workflow_id == workflow_id,
                WorkflowStepsInfo.step_name == step["step_name"]).first()
            if not workflow_step_obj:
                workflow_step_obj = WorkflowStepsInfo(
                    workflow_id=workflow_id,
                    step_name=step["step_name"],
                    info=step["step_info"],
                    created_by=username,
                    created_at=datetime.now(),
                )
            else:
                workflow_step_obj.info = step["step_info"]
                workflow_step_obj.updated_by = username
                workflow_step_obj.updated_at = datetime.now()

            db.add(workflow_step_obj)
            db.commit()
            db.refresh(workflow_step_obj)
            step_data_list.append(workflow_step_obj)
        except Exception as e:
            errors.append(e)

    return errors, step_data_list


def ensure_status_record(db, user_id, user_workflow_history_obj):
    if user_id is None:
        return
    exists = any(sr.user_id == user_id for sr in user_workflow_history_obj.status_records)
    if not exists:
        status_record = UserWorkflowHistoryStatus(
            history=user_workflow_history_obj,
            user_id=user_id,
            unread_flag=True
        )
        db.add(status_record)


def upsert_user_workflow_history_data(workflow_history_data, current_user, db=None):
    if not db:
        db = get_db()
    workflow_info_obj = db.query(WorkflowInfo).filter(
        WorkflowInfo.workflow_name == workflow_history_data["workflow_name"]
    ).first()

    if not workflow_info_obj:
        raise ValueError(f"Workflow with name {workflow_history_data['workflow_name']} not found")

    filters = [
        UserWorkflowHistory.request_id == workflow_history_data["request_id"],
        UserWorkflowHistory.workflow_id == workflow_info_obj.id,
        UserWorkflowHistory.user_query == workflow_history_data["user_query"],
    ]
    
    if workflow_history_data.get("info"):
        for key, value in workflow_history_data["info"].items():
            if isinstance(value, list):
                array_conditions = []
                for item in value:
                    array_conditions.append(UserWorkflowHistory.info[key].op('?')(str(item)))
                if array_conditions:
                    filters.append(or_(*array_conditions))
            else:
                filters.append(UserWorkflowHistory.info[key].astext == str(value))
    
    user_workflow_history_obj = db.query(UserWorkflowHistory).filter(*filters).first()

    approver_id = None
    if workflow_history_data.get("approver_name"):
        approver_obj = db.query(User).filter(User.username == workflow_history_data["approver_name"]).first()
        if not approver_obj:
            raise ValueError(f"Approver with name {workflow_history_data['approver_name']} not found")
        approver_id = approver_obj.id

    is_etter_generated = workflow_history_data.get("is_etter_generated", False)
    approval_status = workflow_history_data.get("approval_status", "Pending")
    modeling_state_str = workflow_history_data.get("modeling_state", "INITIAL")
    modeling_state = ModelingState(modeling_state_str) if modeling_state_str in [e.value for e in ModelingState] else ModelingState.INITIAL
    score = 0
    if (approval_status.lower() == 'approved' or is_etter_generated) and user_workflow_history_obj:
        data = db.query(UserWorkflowStepsHistory).filter(
            UserWorkflowStepsHistory.user_workflow_history_id == user_workflow_history_obj.id,
            UserWorkflowStepsHistory.type == 'data'
        ).all()
        for step in data:
            if step.data and isinstance(step.data, dict) and 'data' in step.data:
                inner = step.data.get('data')
                if isinstance(inner, dict):
                    score = inner.get('ai_automation_score', 0)
                else:
                    score = getattr(inner, 'ai_automation_score', 0)
    if not user_workflow_history_obj:
        user_workflow_history_obj = UserWorkflowHistory(
            workflow_id=workflow_info_obj.id,
            user_id=workflow_history_data["user_id"],
            request_id=workflow_history_data["request_id"],
            user_query=workflow_history_data["user_query"],
            workflow_status=workflow_history_data["workflow_status"],
            approval_status=workflow_history_data["approval_status"],
            approver_id=approver_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_etter_generated=is_etter_generated,
            score=score if score else None,
            info=workflow_history_data.get("info"),
            modeling_state=modeling_state
        )
        db.add(user_workflow_history_obj)
    else:
        user_workflow_history_obj.workflow_status = workflow_history_data["workflow_status"]
        user_workflow_history_obj.approval_status = approval_status
        user_workflow_history_obj.updated_at = datetime.now()
        user_workflow_history_obj.updated_by = current_user
        user_workflow_history_obj.is_etter_generated = is_etter_generated
        user_workflow_history_obj.score = score
        user_workflow_history_obj.modeling_state = modeling_state
        if workflow_history_data.get("info") is not None:
            user_workflow_history_obj.info = workflow_history_data["info"]
        if approver_id:
            user_workflow_history_obj.approver_id = approver_id

    ensure_status_record(db, workflow_history_data["user_id"], user_workflow_history_obj)
    ensure_status_record(db, approver_id, user_workflow_history_obj)
    db.commit()
    db.refresh(user_workflow_history_obj)
    return user_workflow_history_obj


def update_user_workflow_step_history_data(workflow_step_data, db):
    update_version = workflow_step_data.get("update_version", False)

    if not db:
        db = get_db()

    workflow_info_obj = db.query(WorkflowInfo).filter(
        WorkflowInfo.workflow_name == workflow_step_data["workflow_name"]
    ).first()
    if not workflow_info_obj:
        raise ValueError(f"Workflow with name {workflow_step_data['workflow_name']} not found")

    user_workflow_history_obj = db.query(UserWorkflowHistory).filter(
        UserWorkflowHistory.request_id == workflow_step_data["request_id"],
        UserWorkflowHistory.workflow_id == workflow_info_obj.id,
        UserWorkflowHistory.user_query == workflow_step_data["user_query"],
    ).first()

    if not user_workflow_history_obj:
        raise ValueError(
            "User workflow history not found for the given request_id, workflow_name, user_id, and user_query")

    workflow_step_info_obj = db.query(WorkflowStepsInfo).filter(
        WorkflowStepsInfo.step_name == workflow_step_data["workflow_step_name"]
    ).first()

    data_value = workflow_step_data["data"]
    if isinstance(data_value, str):
        try:
            json.loads(data_value)
        except json.JSONDecodeError:
            data_value = {"content": data_value}
    elif not isinstance(data_value, dict):
        data_value = {"content": str(data_value)}

    workflow_step_data["user_workflow_history_id"] = user_workflow_history_obj.id
    workflow_status = {workflow_step_data.get("workflow_step_status", "pending"): datetime.now().isoformat()}
    version_id = workflow_step_data.get("version_id", 1)

    user_workflow_step_history_obj = None

    if update_version:
        version_id += 1
        create_new_version_for_steps(
            request_id=workflow_step_data["request_id"],
            workflow_name=workflow_step_data["workflow_name"],
            new_version_id=version_id,
            db=db,
            target_step_info_id=workflow_step_info_obj.id,
            new_data=data_value,
            new_status=workflow_status
        )
        for status in user_workflow_history_obj.status_records:
            status.unread_flag = False if status.user_id == workflow_step_data["user_id"] else True

        user_workflow_history_obj.updated_at = datetime.now()
        db.add(user_workflow_history_obj)
        db.commit()

        latest_steps_raw = db.query(UserWorkflowStepsHistory).filter(
            UserWorkflowStepsHistory.user_workflow_history_id == user_workflow_history_obj.id,
            UserWorkflowStepsHistory.version_id == version_id,
            UserWorkflowStepsHistory.is_latest == True
        ).all()
        return latest_steps_raw
    else:
        if workflow_step_info_obj:
            user_workflow_step_history_obj = db.query(UserWorkflowStepsHistory).filter(
                UserWorkflowStepsHistory.user_workflow_history_id == user_workflow_history_obj.id,
                UserWorkflowStepsHistory.workflow_step_info_id == workflow_step_info_obj.id,
                UserWorkflowStepsHistory.is_latest == True,
                UserWorkflowStepsHistory.version_id == version_id,
            ).first()

        if not user_workflow_step_history_obj:
            user_workflow_step_history_obj = UserWorkflowStepsHistory(
                workflow_step_info_id=workflow_step_info_obj.id if workflow_step_info_obj else None,
                type=workflow_step_data["data_type"],
                version_id=version_id,
                user_workflow_history_id=user_workflow_history_obj.id,
                data=data_value,
                workflow_step_status=workflow_status,
                is_latest=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        else:
            user_workflow_step_history_obj.type = workflow_step_data["data_type"]
            user_workflow_step_history_obj.data = data_value
            user_workflow_step_history_obj.workflow_step_status = workflow_status
            user_workflow_step_history_obj.is_latest = True
            user_workflow_step_history_obj.updated_at = datetime.now()
            user_workflow_step_history_obj.version_id = version_id

        db.add(user_workflow_step_history_obj)

    db.commit()
    db.refresh(user_workflow_step_history_obj)

    for status in user_workflow_history_obj.status_records:
        status.unread_flag = False if status.user_id == workflow_step_data["user_id"] else True

    user_workflow_history_obj.updated_at = datetime.now()
    db.add(user_workflow_history_obj)
    db.commit()

    return user_workflow_step_history_obj


def create_new_version_for_steps(
        request_id: str,
        workflow_name: str,
        new_version_id: int,
        db: any,
        target_step_info_id: int,
        new_data: dict,
        new_status: dict
):
    if not db:
        db = get_db()

    workflow_info_obj = db.query(WorkflowInfo).filter(
        WorkflowInfo.workflow_name == workflow_name
    ).first()
    if not workflow_info_obj:
        raise ValueError(f"Workflow with name {workflow_name} not found")

    user_workflow_history_obj = db.query(UserWorkflowHistory).filter(
        UserWorkflowHistory.request_id == request_id,
        UserWorkflowHistory.workflow_id == workflow_info_obj.id,
    ).first()
    if not user_workflow_history_obj:
        raise ValueError(f"UserWorkflowHistory not found for request_id {request_id}")

    existing_steps = db.query(UserWorkflowStepsHistory).filter(
        UserWorkflowStepsHistory.user_workflow_history_id == user_workflow_history_obj.id,
        UserWorkflowStepsHistory.is_latest == True,
        UserWorkflowStepsHistory.version_id == new_version_id - 1,
    ).order_by(UserWorkflowStepsHistory.id).all()

    updated_step_obj = None
    target_step_found = False

    for step in existing_steps:
        step.is_latest = False
        step.updated_at = datetime.now()

        if (
                step.data
                and isinstance(step.data, dict)
                and isinstance(step.data.get("expectedResponse"), list)
        ):
            step.data["expectedResponse"] = [
                {**resp, "editable": False} for resp in step.data["expectedResponse"] if isinstance(resp, dict)
            ]

        db.add(step)

    for step in existing_steps:
        if step.type == 'data':
            new_step_data = copy.deepcopy(step.data)
            new_step_status = step.workflow_step_status

            if step.workflow_step_info_id == target_step_info_id:
                new_step_data = new_data
                target_step_found = True
            elif step.workflow_step_info_id > target_step_info_id and isinstance(new_step_data, dict):
                new_step_data["isPreviousUpdated"] = True
            new_step_data['versionId'] = new_version_id

            new_step = UserWorkflowStepsHistory(
                workflow_step_info_id=step.workflow_step_info_id,
                user_workflow_history_id=step.user_workflow_history_id,
                version_id=new_version_id,
                type=step.type,
                data=new_step_data,
                workflow_step_status=new_step_status,
                is_latest=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db.add(new_step)

    if not target_step_found:
        raise ValueError(f"Target step with id {target_step_info_id} not found in previous version")

    db.commit()
    return updated_step_obj


def get_sample_data(
    db: Session,
    title: Optional[str] = None,
    role: Optional[str] = None
) -> List[SampleData]:
    query = db.query(SampleData)
    
    if title:
        query = query.filter(SampleData.title == title)
    if role:
        query = query.filter(SampleData.role == role)
    
    return query.all()


def bulk_upsert_sample_data(
    db: Session,
    items: List[Dict[str, Any]]
) -> List[SampleData]:
    company_name_to_id = {}
    
    company_names = [item.get('company_name') for item in items if item.get('company_name')]
    unique_company_names = list(set(company_names))
    
    if unique_company_names:
        companies = db.query(MasterCompany).filter(
            MasterCompany.company_name.in_(unique_company_names)
        ).all()
        company_name_to_id = {company.company_name: company.id for company in companies}
    
    results = []
    for item in items:
        company_id = None
        if item.get('company_name'):
            company_id = company_name_to_id.get(item['company_name'])
            if company_id is None:
                raise ValueError(f"Company with name '{item['company_name']}' not found")
        
        existing = db.query(SampleData).filter(
            SampleData.title == item['title'],
            SampleData.role == item['role'],
            SampleData.company_id == company_id
        ).first()
        
        if existing:
            if 'is_global' in item:
                existing.is_global = item['is_global']
            if 'data' in item:
                existing.data = item['data']
            if 'company_name' in item:
                existing.company_id = company_id
            existing.updated_on = datetime.now()
            db.add(existing)
            results.append(existing)
        else:
            new_record = SampleData(
                title=item['title'],
                role=item['role'],
                is_global=item.get('is_global', False),
                data=item['data'],
                company_id=company_id,
                updated_on=datetime.now()
            )
            db.add(new_record)
            results.append(new_record)
    
    db.commit()
    for result in results:
        db.refresh(result)
    
    return results


def check_titles_availability(
    db: Session,
    titles: List[str],
    company_id: Optional[int] = None
) -> Dict[str, bool]:
    if not titles:
        return {}
    
    query = db.query(SampleData.title).filter(SampleData.title.in_(titles))
    
    if company_id is not None:
        query = query.filter(
            or_(
                SampleData.company_id == company_id,
                SampleData.is_global == True
            )
        )
    else:
        query = query.filter(SampleData.is_global == True)
    
    existing_titles = {row[0] for row in query.distinct().all()}
    
    result = {title: title in existing_titles for title in titles}
    
    return result


def bulk_upsert_workflow_builder_sample_data(
    db: Session,
    items: List[Dict[str, Any]],
    company_name: Optional[str],
    current_user: User
) -> List[WorkflowBuilderSampleData]:
    company_id = None
    if company_name:
        company = db.query(MasterCompany).filter(MasterCompany.company_name == company_name).first()
        if not company:
            raise ValueError(f"Company with name '{company_name}' not found")
        company_id = company.id
    
    results = []
    
    for item in items:
        high_level_func = item.get('high_level_func')
        sub_level_func = item.get('sub_level_func')
        is_global = item.get('is_global', False)
        data = item.get('data')
        
        if not high_level_func or not sub_level_func:
            raise ValueError("high_level_func and sub_level_func are required")
        
        if not data:
            raise ValueError("data is required")
        
        master_function = db.query(MasterFunction).filter(
            MasterFunction.high_level_func == high_level_func,
            MasterFunction.sub_level_func == sub_level_func
        ).first()
        
        if not master_function:
            raise ValueError(f"MasterFunction with high_level_func '{high_level_func}' and sub_level_func '{sub_level_func}' not found")
        
        existing = db.query(WorkflowBuilderSampleData).filter(
            WorkflowBuilderSampleData.master_function_id == master_function.id,
            WorkflowBuilderSampleData.company_id == company_id
        ).first()
        
        if existing:
            existing.is_global = is_global
            existing.data = data
            existing.company_id = company_id
            existing.modified_by = current_user.username
            db.add(existing)
            results.append(existing)
        else:
            new_record = WorkflowBuilderSampleData(
                master_function_id=master_function.id,
                is_global=is_global,
                data=data,
                company_id=company_id,
                created_by=current_user.username,
                modified_by=current_user.username
            )
            db.add(new_record)
            results.append(new_record)
    
    db.commit()
    for result in results:
        db.refresh(result)
    
    return results


def delete_workflow_builder_sample_data(
    db: Session,
    id: Optional[int] = None,
    company_name: Optional[str] = None,
    high_level_func: Optional[str] = None,
    sub_level_func: Optional[str] = None
) -> int:
    query = db.query(WorkflowBuilderSampleData)
    
    if id is not None:
        query = query.filter(WorkflowBuilderSampleData.id == id)
    
    if company_name:
        company = db.query(MasterCompany).filter(MasterCompany.company_name == company_name).first()
        if not company:
            raise ValueError(f"Company with name '{company_name}' not found")
        query = query.filter(WorkflowBuilderSampleData.company_id == company.id)
    
    if high_level_func or sub_level_func:
        master_function_query = db.query(MasterFunction)
        if high_level_func:
            master_function_query = master_function_query.filter(MasterFunction.high_level_func == high_level_func)
        if sub_level_func:
            master_function_query = master_function_query.filter(MasterFunction.sub_level_func == sub_level_func)
        
        master_functions = master_function_query.all()
        if not master_functions:
            return 0
        
        master_function_ids = [mf.id for mf in master_functions]
        query = query.filter(WorkflowBuilderSampleData.master_function_id.in_(master_function_ids))
    
    deleted_count = query.count()
    query.delete(synchronize_session=False)
    db.commit()
    
    return deleted_count


def delete_sample_data_by_id(
    db: Session,
    sample_data_id: int
) -> bool:
    record = db.query(SampleData).filter(SampleData.id == sample_data_id).first()
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


def _get_consolidated_tasks_for_role(
    company: str,
    role: str,
    token: str
) -> Dict[str, Any]:
    """
    Get consolidated tasks from task consolidator and filter by role.

    Args:
        company: Company name
        role: Role name to filter by
        token: Auth token for API

    Returns:
        Dictionary with tasks list or error
    """
    from api.etter_apis import get_draup_world_api

    try:
        # Call draup_world_model API for task consolidator
        target_url = f"{get_draup_world_api()}/workflows"
        headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "workflow": "task_consolidator",
            "step": "get_consolidated_tasks",
            "data": {
                "company": company,
                "refresh_cache": False
            }
        }

        response = requests.post(target_url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()

            # Extract consolidated tasks from response
            consolidated_tasks_table = result.get("current_step", {}).get("data", {}).get("consolidated_tasks_table", {})
            body = consolidated_tasks_table.get("body", [])

            if not body:
                return {
                    "error": "No consolidated tasks found",
                    "error_code": "NO_TASKS"
                }

            # Filter tasks where the role is present in the "Roles" field
            filtered_tasks = []
            for row in body:
                if not isinstance(row, dict):
                    continue

                task_name = row.get("Task", "")
                roles_field = row.get("Roles", "")
                automation_type = row.get("Automation Type", "")

                if not task_name or not task_name.strip():
                    continue

                # Check if the role is present in the comma-separated Roles field
                if roles_field and isinstance(roles_field, str):
                    # Split by comma and strip whitespace from each role
                    roles_list = [r.strip() for r in roles_field.split(",")]

                    # Check if the target role matches any role in the list (case-insensitive)
                    if any(role.lower() == r.lower() for r in roles_list):
                        # Map automation type to Human/AI/Human+AI
                        task_type = _map_task_type_to_human_ai(automation_type)

                        filtered_tasks.append({
                            "task": task_name.strip(),
                            "task_type": task_type
                        })

            return {
                "tasks": filtered_tasks
            }
        else:
            logger.error(f"Task consolidator API call failed with status {response.status_code}: {response.text}")
            return {
                "error": f"Failed to fetch consolidated tasks: {response.text}",
                "error_code": "API_ERROR"
            }

    except requests.exceptions.Timeout:
        logger.error("Request to task consolidator API timed out")
        return {
            "error": "Request timed out",
            "error_code": "TIMEOUT"
        }
    except Exception as e:
        logger.error(f"Error in _get_consolidated_tasks_for_role: {str(e)}")
        return {
            "error": f"Error fetching consolidated tasks: {str(e)}",
            "error_code": "INTERNAL_ERROR"
        }


def get_tasks_from_sources(
    company: Optional[str],
    role: Optional[str],
    workflow_id: Optional[int],
    workflow_name: Optional[str],
    function_id: Optional[int],
    db: Session,
    limit: Optional[int] = 20,
    is_autocomplete: bool = False
) -> Dict[str, Any]:
    """
    Retrieve tasks from three possible sources with priority logic:
    1. Role-based tasks from Neo4j (via draup_world_model API) if role and company provided
    2. Workflow-based tasks from Postgres if workflow_id or workflow_name provided
    3. Task consolidator (top tasks) if only company provided

    Args:
        company: Company name (optional)
        role: Role name (optional)
        workflow_id: Workflow ID for postgres lookup (optional)
        workflow_name: Workflow name for postgres lookup (optional, requires function_id)
        function_id: Function ID required when using workflow_name (optional)
        db: Database session
        limit: Maximum number of tasks to return (default 20, None for all tasks)

    Returns:
        Dictionary with source, tasks list, and metadata
    """
    from api.etter_apis import get_token, get_draup_world_api
    
    # If workflow_name is provided but workflow_id is not, look up the workflow_id
    if workflow_name and not workflow_id:
        # Require function_id when using workflow_name
        if not function_id:
            return {
                "error": "function_id is required when using workflow_name (workflow names are only unique within a function)",
                "error_code": "INVALID_PARAMETERS"
            }
        
        try:
            workflow = db.query(FunctionWorkflow).filter(
                FunctionWorkflow.workflow_name == workflow_name,
                FunctionWorkflow.function_id == function_id
            ).first()
            
            if workflow:
                workflow_id = workflow.id
                logger.info(f"Resolved workflow_name '{workflow_name}' (function_id {function_id}) to workflow_id {workflow_id}")
            else:
                return {
                    "error": f"Workflow with name '{workflow_name}' not found for function_id {function_id}",
                    "error_code": "WORKFLOW_NOT_FOUND"
                }
        except Exception as e:
            logger.error(f"Error looking up workflow_name: {str(e)}")
            return {
                "error": f"Database error while looking up workflow: {str(e)}",
                "error_code": "DATABASE_ERROR"
            }
    
    # Priority 1: Role-based tasks (requires both company and role)
    if role and company:
        try:
            logger.info(f"Fetching role-based tasks for {role} at {company}")
            
            # Get auth token
            token = get_token()
            if not token:
                return {
                    "error": "Failed to obtain auth token for draup_world API",
                    "error_code": "AUTH_FAILED"
                }
            
            # Call draup_world_model API for role assessment data
            target_url = f"{get_draup_world_api()}/workflows"
            headers = {
                "Authorization": f"Token {token}",
                "Content-Type": "application/json"
            }
            payload = {
                "workflow": "role_assessment_data",
                "step": "get_complete_assessment_data",
                "data": {
                    "company": company,
                    "role": role
                }
            }
            
            response = requests.post(target_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()

                # Extract task analysis from response
                assessment_data = result.get("current_step", {}).get("data", {}).get("assessment_data", {}).get("current_version", {})
                task_analysis = assessment_data.get("task_analysis", {})

                # Parse task analysis table
                tasks = _parse_task_analysis_table(task_analysis)

                # Apply limit if specified
                if limit is not None and not is_autocomplete:
                    tasks = tasks[:limit]
                
                # If no tasks found, fallback to task consolidator filtered by role
                if not tasks:
                    logger.info(f"No role-based tasks found for {role} at {company}, falling back to task consolidator")
                    fallback_result = _get_consolidated_tasks_for_role(company, role, token)

                    if "error" in fallback_result:
                        # If fallback also fails, return the original empty result
                        logger.warning(f"Fallback to task consolidator also failed: {fallback_result.get('error')}")
                        return {
                            "source": "role",
                            "tasks": [],
                            "metadata": {
                                "company": company,
                                "role": role,
                                "total_tasks": 0,
                                "source_type": "role_assessment_neo4j",
                                "fallback_attempted": True,
                                "fallback_error": fallback_result.get("error")
                            }
                        }

                    # Use fallback tasks
                    tasks = fallback_result.get("tasks", [])

                    # Limit to max 20 tasks
                    if not is_autocomplete:
                        tasks = tasks[:20]

                    return {
                        "source": "role_consolidated_fallback",
                        "tasks": tasks,
                        "metadata": {
                            "company": company,
                            "role": role,
                            "total_tasks": len(tasks),
                            "source_type": "task_consolidator_filtered_by_role",
                            "fallback_used": True
                        }
                    }

                # Limit to max 20 tasks
                if not is_autocomplete:
                    tasks = tasks[:20]

                # Apply limit if specified
                if limit is not None and not is_autocomplete:
                    tasks = tasks[:limit]
                
                return {
                    "source": "role",
                    "tasks": tasks,
                    "metadata": {
                        "company": company,
                        "role": role,
                        "total_tasks": len(tasks),
                        "source_type": "role_assessment_neo4j"
                    }
                }
            elif response.status_code == 404:
                return {
                    "error": f"Role '{role}' not found for company '{company}'",
                    "error_code": "ROLE_NOT_FOUND"
                }
            else:
                logger.error(f"API call failed with status {response.status_code}: {response.text}")
                return {
                    "error": f"Failed to fetch role assessment data: {response.text}",
                    "error_code": "API_ERROR"
                }
                
        except requests.exceptions.Timeout:
            logger.error("Request to draup_world API timed out")
            return {
                "error": "Request timed out",
                "error_code": "TIMEOUT"
            }
        except Exception as e:
            logger.error(f"Error fetching role-based tasks: {str(e)}")
            return {
                "error": f"Error fetching role-based tasks: {str(e)}",
                "error_code": "INTERNAL_ERROR"
            }
    
    # Priority 2: Workflow-based tasks from Postgres
    elif workflow_id:
        try:
            logger.info(f"Fetching workflow-based tasks for workflow_id {workflow_id}")
            
            workflow_tasks = db.query(WorkflowTask).filter(
                WorkflowTask.workflow_id == workflow_id
            ).order_by(WorkflowTask.position).all()
            
            if not workflow_tasks:
                return {
                    "error": f"No tasks found for workflow_id {workflow_id}",
                    "error_code": "WORKFLOW_NOT_FOUND"
                }
            
            tasks = []
            for task in workflow_tasks:
                # Map task_type from database to Human/AI/Human+AI format
                task_type = _map_task_type_to_human_ai(task.task_type)
                
                tasks.append({
                    "task": task.task_name,
                    "task_type": task_type
                })

            # Apply limit if specified
            if limit is not None and not is_autocomplete:
                tasks = tasks[:limit]
            
            # Get workflow details for metadata
            workflow = db.query(FunctionWorkflow).filter(
                FunctionWorkflow.id == workflow_id
            ).first()
            
            metadata = {
                "workflow_id": workflow_id,
                "total_tasks": len(tasks),
                "source_type": "postgres_workflow"
            }
            
            if workflow:
                metadata["workflow_name"] = workflow.workflow_name
                metadata["function_id"] = workflow.function_id
            
            return {
                "source": "workflow",
                "tasks": tasks,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error fetching workflow tasks: {str(e)}")
            return {
                "error": f"Database error: {str(e)}",
                "error_code": "DATABASE_ERROR"
            }
    
    # Priority 3: Task consolidator (top tasks)
    elif company:
        try:
            logger.info(f"Fetching consolidated tasks for {company}")
            
            # Get auth token
            token = get_token()
            if not token:
                return {
                    "error": "Failed to obtain auth token for draup_world API",
                    "error_code": "AUTH_FAILED"
                }
            
            # Call draup_world_model API for task consolidator
            target_url = f"{get_draup_world_api()}/workflows"
            headers = {
                "Authorization": f"Token {token}",
                "Content-Type": "application/json"
            }
            payload = {
                "workflow": "task_consolidator",
                "step": "get_consolidated_tasks",
                "data": {
                    "company": company,
                    "refresh_cache": False
                }
            }
            
            response = requests.post(target_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract consolidated tasks from response
                consolidated_tasks_table = result.get("current_step", {}).get("data", {}).get("consolidated_tasks_table", {})
                
                # Parse consolidated tasks table
                tasks = _parse_consolidated_tasks_table(consolidated_tasks_table)

                # Apply limit if specified
                if limit is not None and not is_autocomplete:
                    tasks = tasks[:limit]
                
                return {
                    "source": "consolidator",
                    "tasks": tasks,
                    "metadata": {
                        "company": company,
                        "total_tasks": len(tasks),
                        "source_type": "task_consolidator"
                    }
                }
            else:
                logger.error(f"API call failed with status {response.status_code}: {response.text}")
                return {
                    "error": f"Failed to fetch consolidated tasks: {response.text}",
                    "error_code": "API_ERROR"
                }
                
        except requests.exceptions.Timeout:
            logger.error("Request to draup_world API timed out")
            return {
                "error": "Request timed out",
                "error_code": "TIMEOUT"
            }
        except Exception as e:
            logger.error(f"Error fetching consolidated tasks: {str(e)}")
            return {
                "error": f"Error fetching consolidated tasks: {str(e)}",
                "error_code": "INTERNAL_ERROR"
            }
    
    # No valid parameters provided
    else:
        return {
            "error": "Invalid parameters: provide either (company + role), workflow_id/workflow_name, or company",
            "error_code": "INVALID_PARAMETERS"
        }


def _map_task_type_to_human_ai(task_type: Optional[str]) -> str:
    """
    Map task automation category to Human/AI/Human+AI format.
    
    Mapping rules:
    - Directive → AI
    - Feedback Loop → AI
    - Task Iteration → Human+AI
    - Learning → Human+AI
    - Validation → Human+AI
    - Negligibility → Human
    
    Args:
        task_type: Task automation category (e.g., "Directive", "Feedback Loop", etc.)
    
    Returns:
        Mapped task type: "AI", "Human", or "Human+AI"
    """
    if not task_type:
        return "Human+AI"  # Default for unknown types
    
    # Normalize the input (remove emojis, spaces, handle case variations)
    normalized = task_type.lower().strip()
    
    # Remove common emojis
    normalized = normalized.replace("🤖", "").replace("👤", "").strip()
    
    # Map to Human/AI/Human+AI
    if "directive" in normalized:
        return "AI"
    elif "feedback" in normalized or "feedback loop" in normalized:
        return "AI"
    elif "task iteration" in normalized or "iteration" in normalized:
        return "Human+AI"
    elif "learning" in normalized:
        return "Human+AI"
    elif "validation" in normalized:
        return "Human+AI"
    elif "negligibility" in normalized or "negligible" in normalized:
        return "Human"
    else:
        # Default to Human+AI for unknown categories
        logger.warning(f"Unknown task type '{task_type}', defaulting to 'Human+AI'")
        return "Human+AI"


def _parse_task_analysis_table(task_analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Parse task analysis table structure to extract individual task names with their types.
    
    Task analysis structure has 'task_analysis_table' as a JSON string containing 'headers' and 'body'.
    Body is an array of objects with emoji keys like "Directive 🤖", "Feedback Loop 🤖", etc.
    
    Returns:
        List of task dictionaries with 'task' and 'task_type' keys
    """
    tasks = []
    
    if not task_analysis or not isinstance(task_analysis, dict):
        return tasks
    
    # First, parse the JSON string to get the actual table structure
    try:
        if "task_analysis_table" in task_analysis:
            task_analysis_data = json.loads(task_analysis["task_analysis_table"])
        else:
            # Fallback if it's already parsed
            task_analysis_data = task_analysis
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Error parsing task_analysis_table JSON: {e}")
        return tasks
    
    body = task_analysis_data.get("body", [])
    if not body:
        return tasks
    
    # Mapping of emoji keys to clean automation types
    automation_type_mapping = {
        "Directive 🤖": "Directive",
        "Feedback Loop 🤖": "Feedback Loop",
        "Task Iteration 🤖+👤": "Task Iteration",
        "Learning 🤖+👤": "Learning",
        "Validation 🤖+👤": "Validation",
        "Negligibility 👤": "Negligibility"
    }
    
    # Each row in body is an object with emoji keys
    for row in body:
        if not isinstance(row, dict):
            continue
        
        # Process each automation type
        for emoji_key, automation_type in automation_type_mapping.items():
            task_content = row.get(emoji_key)

            if task_content and isinstance(task_content, str) and task_content.strip():
                # Map automation type to Human/AI/Human+AI
                task_type = _map_task_type_to_human_ai(automation_type)

                # Split by semicolon to handle multiple tasks in a single cell
                individual_tasks = [t.strip() for t in task_content.split(';') if t.strip()]

                for task_name in individual_tasks:
                    tasks.append({
                        "task": task_name,
                        "task_type": task_type
                    })
    
    return tasks


def _parse_consolidated_tasks_table(consolidated_tasks_table: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Parse consolidated tasks table structure to extract individual task names with their types.
    
    Consolidated tasks table structure has a JSON string that contains 'headers' and 'body'.
    Body contains dictionaries with keys: 'Task', 'Automation Type', 'Workloads', 'Occurrence', 'Roles'.
    
    Returns:
        List of task dictionaries with 'task' and 'task_type' keys
    """
    tasks = []
    
    if not consolidated_tasks_table or not isinstance(consolidated_tasks_table, dict):
        return tasks
    
    # Parse the JSON string from consolidated_tasks_table
    try:
        if "consolidated_tasks_table" in consolidated_tasks_table:
            table_data = json.loads(consolidated_tasks_table["consolidated_tasks_table"])
        else:
            table_data = consolidated_tasks_table
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Error parsing consolidated_tasks_table JSON: {str(e)}")
        return tasks
    
    body = table_data.get("body", [])
    if not body:
        return tasks
    
    # Each row in body represents a consolidated task
    for row in body:
        if not isinstance(row, dict):
            continue
        
        task_name = row.get("Task", "")
        if not task_name or not task_name.strip():
            continue
        
        # Extract automation type and map to Human/AI/Human+AI
        automation_type = row.get("Automation Type", "")
        task_type = _map_task_type_to_human_ai(automation_type)
        
        tasks.append({
            "task": task_name.strip(),
            "task_type": task_type
        })
    
    return tasks
