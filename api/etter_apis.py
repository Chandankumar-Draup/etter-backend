import base64
import math
from datetime import datetime, timedelta
from statistics import median
from typing import Optional, List, Dict, Union

import json
from common.logger import logger
import hashlib
import requests

from fastapi import APIRouter, status, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from services.auth import ResponseModel
from sqlalchemy.orm import (
    Session,
    selectinload,
    joinedload,
    InstrumentedAttribute,
    aliased,
)
import os
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, Response
import httpx
from uuid import uuid4
import uuid

from common.common_utils import get_minimized_time_ago
from common.pagination import paginate
from models.auth import User

from ml_models.simulation import SimulationRequestData
from ml_models.role_adjacency import PredictedRole, RoleAdjacencyException
from ml_models.role_adjacency.role_adjacency import get_similar_roles_async

from services.simulation.store import get_sim_store
from services.role_adjaceny_service import get_adjacent_roles_cacheable
from services.simulation.simulation_service import run_and_store_simulation
from services.task_simulation_score_service import compute_task_simulator_scores_service
from models.etter import (
    UserWorkflowHistory,
    WorkflowInfo,
    UserWorkflowStepsHistory,
    WorkflowStepsInfo,
    UserWorkflowHistoryStatus,
    MasterCompany,
    MasterFunction,
    FinancialSimulator,
    RoleAdjacency,
    SampleData,
    TaskFeasibility,
    Function,
    FunctionWorkflow,
    WorkflowTask,
)
from services.etter import (
    delete_sample_data_by_id,
    upsert_workflow_info,
    create_new_version_for_steps,
    ensure_status_record,
    fetchMasterCompanyData,
    fetchMasterFunctionData,
    fetchTableData,
    get_sample_data,
    bulk_upsert_sample_data,
    check_titles_availability,
)
from services.autocomplete_service import fetch_autocomplete_data
from schemas.etter_schemas import (
    CreateNewWorkflow,
    UpsertUserWorkflowHistory,
    UpsertUserWorkflowStepHistory,
    UserWorkflowFilters,
    UserWorkflowStepFilters,
    UserWorkflowHistoryFilters,
    AutoCompleteFilters,
    FetchAutocompleteDataRequest,
    RefreshTaskAutocompleteRequest,
    MasterCompanyData,
    TableDataRequest,
    SimulationRequest,
    CompanySimulationRequest,
    CompanySimulationRequest,
    RoleAdjacencyRequest,
    FetchAdjacencyRequest,
    SampleDataFilter,
    SampleDataBulkUpsertRequest,
    SampleDataResponse,
    SampleDataTitleCheckRequest,
    TaskSimulatorScoresRequest,
    TaskSimulatorScoresResponse,
    WorkflowBuilderProcessRequest,
    ComprehensiveFunctionWorkflowCreate,
    EnrichTasksRequest,
    TaskCreate,
    RecalculateScoreRequest,
    DynamicProxyRequest,
)

from settings.database import get_db
from services.auth import verify_token
from services.etter import (
    upsert_workflow_step,
    upsert_user_workflow_history_data,
    update_user_workflow_step_history_data,
)
from constants.etter import DRAUP_WORLD_API, DRAUP_WORLD_API_QA, DRAUP_WORLD_USERNAME, DRAUP_WORLD_PASSWORD, TASK_FEASIBILITY_STALE_DAYS
from common.common_utils import getCurrentEnvironment
from sqlalchemy import or_, func, asc, case, distinct
from services.email_service import send_mail_through_draup_services
from api.function_workflow_task_apis import create_comprehensive_workflow, bulk_upsert_tasks
from pydantic import ValidationError
etter_api_router = APIRouter(prefix="/etter", tags=["Etter"])

def get_draup_world_api() -> str:
    if getCurrentEnvironment() == 'prod':
        return DRAUP_WORLD_API
    else:
        return DRAUP_WORLD_API_QA


@etter_api_router.get("/v1/task-feasibility", status_code=status.HTTP_200_OK)
async def get_task_feasibility_runs(company: str, role: Optional[str] = None, task_name: Optional[str] = None, db: Session = Depends(get_db)):
    if not company:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"status": "failure", "errors": ["Company name is required"]})
    companyRecord = db.query(MasterCompany).filter(MasterCompany.company_name == company).first()
    if not companyRecord:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"status": "failure", "errors": ["Company not found"]})

    base_query = db.query(TaskFeasibility).filter(
        TaskFeasibility.company_id == companyRecord.id,
        TaskFeasibility.user_query == role if role else True,
        TaskFeasibility.task_name.like(f"%{task_name}%") if task_name else True,
    )
    runs = base_query.all()
    entries = [{
        "id": run.id,
        "role": run.user_query,
        "task_name": run.task_name,
        "task_type": run.task_type,
        "etter_score": run.etter_score,
        "model_score": run.model_score,
        "median": run.median,
    } for run in runs]
    content = {
        "status": "success",
        "company": company,
        "runs": entries
    }
    if role:
        content["role"] = role
    if task_name:
        content["task_name"] = task_name
    return JSONResponse(status_code=status.HTTP_200_OK, content=content)

@etter_api_router.delete("/v1/task-feasibility/{id}", status_code=status.HTTP_200_OK)
async def delete_task_feasibility_run(id: int, db: Session = Depends(get_db)):

    run = db.query(TaskFeasibility).filter(TaskFeasibility.id == id).first()
    if not run:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"status": "failure", "errors": ["Task feasibility run not found"]})
    try:
        db.delete(run)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete task feasibility run: {e}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": "failure", "errors": ["Failed to delete task feasibility run"]})
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "success", "message": "Task feasibility run deleted successfully"})


@etter_api_router.post("/get/task-feasibility", status_code=status.HTTP_200_OK)
async def get_task_feasibility_data(
    data: TaskSimulatorScoresRequest,
    db: Session = Depends(get_db),
):
    resp_obj = {"status": "success", "data": [], "errors": []}
    company_name = (data.company or "").strip()
    if not company_name:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("company is required")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=resp_obj)
    role_value = (data.role or "").strip()
    if not role_value:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("role is required")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=resp_obj)
    company = db.query(MasterCompany).filter(MasterCompany.company_name == company_name).first()
    if not company:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Company '{company_name}' not found")
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=resp_obj)
    cleaned_tasks = []
    if data.tasks:
        for item in data.tasks:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    cleaned_tasks.append(stripped)

    def serialize(record: TaskFeasibility):
        median_data = record.median or {}
        median_value = median_data.get("median")
        variance_value = median_data.get("variance")
        model_results = record.model_score or []
        if median_value is None and model_results:
            score_values = [entry.get("score") for entry in model_results if isinstance(entry.get("score"), (int, float))]
            if score_values:
                median_value = median(score_values)
        return {
            "task": record.task_name,
            "mean_scores": record.etter_score,
            "variances": variance_value,
            "median": median_value,
            "model_task_results": model_results,
            "task_type": record.task_type,
        }

    base_query = db.query(TaskFeasibility).filter(
        TaskFeasibility.company_id == company.id,
        TaskFeasibility.user_query == role_value,
    )

    if cleaned_tasks:
        existing_records = base_query.filter(TaskFeasibility.task_name.in_(cleaned_tasks)).all()
        existing_map = {record.task_name: record for record in existing_records}
        missing_tasks = [task for task in cleaned_tasks if task not in existing_map]
        record_list = [existing_map[task] for task in cleaned_tasks if task in existing_map]
        stale_records = [
            record for record in record_list if not record.updated_on or (datetime.utcnow() - record.updated_on) > timedelta(days=TASK_FEASIBILITY_STALE_DAYS)
        ]
        if not missing_tasks and len(existing_map) == len(set(cleaned_tasks)) and not stale_records:
            resp_obj["data"] = [serialize(existing_map[task]) for task in cleaned_tasks]
            return resp_obj
    else:
        existing_records = base_query.all()
        stale_records = [
            record for record in existing_records if not record.updated_on or (datetime.utcnow() - record.updated_on) > timedelta(days=TASK_FEASIBILITY_STALE_DAYS)
        ]
        if existing_records and not stale_records:
            resp_obj["data"] = [serialize(record) for record in existing_records]
            return resp_obj

    try:
        llm_results = await compute_task_simulator_scores_service(tasks=cleaned_tasks, company=company_name, role=role_value)
        if not llm_results:
            return resp_obj
        result_tasks = {item.get("task").strip() for item in llm_results if isinstance(item.get("task"), str) and item.get("task").strip()}
        existing_records = base_query.filter(TaskFeasibility.task_name.in_(result_tasks)).all() if result_tasks else []
        existing_map = {record.task_name: record for record in existing_records}
        for result in llm_results:
            task_name = result.get("task")
            if not isinstance(task_name, str):
                continue
            task_name = task_name.strip()
            if not task_name:
                continue
            model_results = result.get("model_task_results") or []
            score_values = [entry.get("score") for entry in model_results if isinstance(entry.get("score"), (int, float))]
            median_value = median(score_values) if score_values else None
            result["median"] = median_value
            median_payload = None
            if median_value is not None or result.get("variances") is not None:
                median_payload = {}
                if median_value is not None:
                    median_payload["median"] = median_value
                if result.get("variances") is not None:
                    median_payload["variance"] = result.get("variances")
            model_payload = model_results if model_results else None
            record = existing_map.get(task_name)
            if record:
                record.task_type = result.get("task_type")
                record.etter_score = result.get("mean_scores")
                record.model_score = model_payload
                record.median = median_payload
                record.updated_on = datetime.utcnow()
            else:
                db.add(
                    TaskFeasibility(
                        company_id=company.id,
                        user_query=role_value,
                        task_name=task_name,
                        task_type=result.get("task_type"),
                        etter_score=result.get("mean_scores"),
                        model_score=model_payload,
                        median=median_payload,
                        updated_on=datetime.utcnow()
                    )
                )
        db.commit()
        resp_obj["data"] = llm_results
        return resp_obj
    except Exception as exc:
        db.rollback()
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error fetching task feasibility: {str(exc)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=resp_obj)


@etter_api_router.post("/v1/task_simulator_scores", status_code=status.HTTP_200_OK, response_model=List[TaskSimulatorScoresResponse])
async def get_task_simulator_scores(data: TaskSimulatorScoresRequest):
    try:
        llm_results = await compute_task_simulator_scores_service(tasks=data.tasks, company=data.company, role=data.role)
        return llm_results
    except Exception as e:

        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting task simulator scores: {str(e)}")

@etter_api_router.post("/role_adjacency/{version}", status_code=status.HTTP_200_OK)   
async def get_role_adjacency(version: str, data: List[RoleAdjacencyRequest], db: Session = Depends(get_db)):

    if version not in ["v1", "v2"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid version: {version}")

    results = []
    for role_adjacency_request in data:
        try:
            role_similar_roles_data = {
                "role": role_adjacency_request.job_role,
                "company": role_adjacency_request.company,
                "top_k": 15,
                "description": role_adjacency_request.description,
                "candidate_roles": role_adjacency_request.candidate_roles
            }
            
            if version == "v2":
                result = await get_similar_roles_async(role_similar_roles_data, version)
            else:
                result = get_adjacent_roles_cacheable(role_similar_roles_data, version)
            top_k = min(role_similar_roles_data["top_k"], 15)
            similar_roles = result[:top_k]
            
            company = db.query(MasterCompany).filter(MasterCompany.company_name == role_adjacency_request.company).first()
            if company:
                adjacency_dict = {role["job_role"]: role["score"] for role in similar_roles}
                
                existing_record = db.query(RoleAdjacency).filter(
                    RoleAdjacency.company_id == company.id,
                    RoleAdjacency.job_role == role_adjacency_request.job_role
                ).first()
                
                if existing_record:
                    existing_record.adjacency_info.update(adjacency_dict)
                    existing_record.updated_on = datetime.utcnow()
                else:
                    new_record = RoleAdjacency(
                        company_id=company.id,
                        job_role=role_adjacency_request.job_role,
                        adjacency_info=adjacency_dict,
                        updated_on=datetime.utcnow()
                    )
                    db.add(new_record)
                
                db.commit()
                
                results.append({
                    "status": "success",
                    "data": {
                        "company_id": company.id,
                        "job_role": role_adjacency_request.job_role,
                        "adjacency_info": adjacency_dict,
                        "updated_on": datetime.utcnow(),
                        "source": "ml_api"
                    }
                })
            else:
                results.append({
                    "status": "error",
                    "message": "Company not found"
                })
            
        except RoleAdjacencyException as e:
            results.append({
                "status": "error",
                "message": str(e)
            })
        except Exception as e:
            results.append({
                "status": "error",
                "message": f"Error getting adjacent roles: {str(e)}"
            })
    
    return results


@etter_api_router.post("/fetch/adjacency", status_code=status.HTTP_200_OK)
async def fetch_adjacency(
    request: FetchAdjacencyRequest,
    db: Session = Depends(get_db)
):
    company_id = request.company_id
    job_role = request.job_role
    version = request.version
    existing_record = db.query(RoleAdjacency).filter(
        RoleAdjacency.company_id == company_id,
        RoleAdjacency.job_role == job_role
    ).first()
    
    if existing_record:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        if existing_record.updated_on > thirty_days_ago:
            return {
                "status": "success",
                "data": {
                    "company_id": existing_record.company_id,
                    "job_role": existing_record.job_role,
                    "adjacency_info": existing_record.adjacency_info,
                    "updated_on": existing_record.updated_on,
                    "source": "database"
                }
            }
        else:
            company = db.query(MasterCompany).filter(MasterCompany.id == company_id).first()
            if company:
                role_adjacency_data = [RoleAdjacencyRequest(
                    job_role=job_role,
                    company=company.company_name,
                    candidate_roles=[]
                )]
                
                try:
                    result = await get_role_adjacency(version, role_adjacency_data, db)
                    if result[0]['status'] == 'error':
                        return {
                            "status": "error",
                            "message": result[0]['message']
                        }
                    return {
                        "status": "success",
                        "data": {
                            "company_id": company_id,
                            "job_role": job_role,
                            "adjacency_info": result[0]['data']["adjacency_info"] if result else [],
                            "updated_on": datetime.utcnow(),
                            "source": "refreshed"
                        }
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Failed to refresh data: {str(e)}"
                    }
            else:
                return {
                    "status": "error",
                    "message": "Company not found"
                }
    else:
        company = db.query(MasterCompany).filter(MasterCompany.id == company_id).first()
        if company:
            role_adjacency_data = [RoleAdjacencyRequest(
                job_role=job_role,
                company=company.company_name,
                candidate_roles=[]
            )]
            
            try:
                result = await get_role_adjacency(version, role_adjacency_data, db)
                if result[0]['status'] == 'error':
                    return {
                        "status": "error",
                        "message": result[0]['message']
                    }
                return {
                    "status": "success",
                    "data": {
                        "company_id": company_id,
                        "job_role": job_role,
                        "adjacency_info": result[0]['data']["adjacency_info"] if result else [],
                        "updated_on": datetime.utcnow(),
                        "source": "created"
                    }
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to create data: {str(e)}"
                }
        else:
            return {
                "status": "error",
                "message": "Company not found"
            }


@etter_api_router.get("/simulation/v1/{sim_id}", status_code=status.HTTP_200_OK)
def get_simulation(sim_id: str,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    existing_simulation = db.query(FinancialSimulator).filter(
        FinancialSimulator.id == sim_id,
        modified_by=current_user.id,
    ).first()
    
    if existing_simulation:
        return existing_simulation.simulation_data

    return {"error": "Simulation ID not found."}


@etter_api_router.post("/simulation/v1", status_code=status.HTTP_200_OK)
async def start_simulation(
    data: SimulationRequest, 
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    """
    Start an asynchronous simulation which is blocking and return the data of the request.
    Saves simulation data with respect to user and updates based on username+company.
    """
    # Generate a unique ID for this simulation run
    sim_id = f"sim-{str(uuid4())}"
    sim_cache_key = f"sim:{hashlib.sha256(data.model_dump_json().encode()).hexdigest()}"
    sim_store = get_sim_store()
    if sim_store.exists(sim_cache_key):
        if sim_store.get(sim_cache_key) is None:
            sim_store.delete(sim_cache_key)
        elif "status" in sim_store.get(sim_cache_key) and sim_store.get(sim_cache_key)["status"] == "completed":
            cached_data = sim_store.get(sim_cache_key)
            return cached_data
        else:
            sim_cache_key = sim_cache_key + "-1"

    simulation_data = SimulationRequestData(
        n_iterations=data.n_iterations,
        company=data.company,
        automation_factor=data.automation_factor,
        roles=[role.model_dump() for role in data.roles],
    )

    sim_store.create(sim_cache_key, id=sim_id, input_data=simulation_data)
    sim_store.update(sim_cache_key, status="in_progress", simulation_steps=[])

    simulation_steps, yearly_metrics, workloads, explanations = await run_and_store_simulation(simulation_data)
    status = "failed"
    if simulation_steps:
        status = "completed"

    sim_store.update(
        sim_cache_key,
        id=sim_id,
        status=status,
        workloads=workloads,
        yearly_metrics=yearly_metrics,
        explanations=explanations,
        simulation_steps=simulation_steps,
    )
    result = sim_store.get(sim_cache_key)
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    # Save to FinancialSimulator if company exists
    if data.company:
        company = db.query(MasterCompany).filter(MasterCompany.company_name == data.company).first()
        if company:
            existing_simulation = db.query(FinancialSimulator).filter(
                FinancialSimulator.company_id == company.id,
                FinancialSimulator.modified_by == current_user.id
            ).first()
            
            if existing_simulation:
                existing_simulation.last_ran_on = datetime.utcnow()
                existing_simulation.simulation_data = result
                db.commit()
            else:
                financial_sim = FinancialSimulator(
                    company_id=company.id,
                    modified_by=current_user.id,
                    last_ran_on=datetime.utcnow(),
                    simulation_data=result
                )
                db.add(financial_sim)
                db.commit()
    
    return result


@etter_api_router.post("/simulation/company", status_code=status.HTTP_200_OK)
def get_simulation_by_company(
    request: CompanySimulationRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    """
    Get simulation data for a specific company by company name.
    First checks for user+company combination, then falls back to company only.
    """
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        # Find the company by name
        company = db.query(MasterCompany).filter(
            MasterCompany.company_name == request.company_name
        ).first()
        
        if not company:
            return {
                "status": "failure",
                "message": f"Company '{request.company_name}' not found",
                "data": None
            }
        
        simulation = db.query(FinancialSimulator).filter(
            FinancialSimulator.company_id == company.id,
            FinancialSimulator.modified_by == current_user.id
        ).first()
        
        if not simulation:
            simulation = db.query(FinancialSimulator).filter(
                FinancialSimulator.company_id == company.id
            ).first()
        
        if not simulation:
            return {
                "status": "failure",
                "message": f"No simulation data found for company '{request.company_name}'",
                "data": None
            }
        
        simulation_data = simulation.simulation_data
        max_roles = request.max_roles if request.max_roles is not None else 5
        
        if simulation_data and isinstance(simulation_data, dict):
            if "input_data" in simulation_data and isinstance(simulation_data["input_data"], dict):
                if "roles" in simulation_data["input_data"] and isinstance(simulation_data["input_data"]["roles"], list):
                    simulation_data["input_data"]["roles"] = simulation_data["input_data"]["roles"][:max_roles]
        
        return {
            "status": "success",
            "message": "Simulation data retrieved successfully",
            "data": simulation_data,
            "last_ran_on": simulation.last_ran_on,
            "company_name": request.company_name,
            "modified_by": simulation.modified_by
        }
        
    except Exception as e:
        return {
            "status": "failure",
            "message": f"Error retrieving simulation data: {str(e)}",
            "data": None
        }


@etter_api_router.get("/test", status_code=status.HTTP_200_OK)
def test():
    return {"message": "Etter API is running successfully!"}


@etter_api_router.post("/update_workflow")
def update_workflow(
    request: Request,
    workflow_info: CreateNewWorkflow,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    resp_obj = {"status": "success", "data": None, "errors": None}

    if request.method != "POST":
        resp_obj["status"] = "failure"
        resp_obj["errors"] = ["Method not allowed"]
        return JSONResponse(resp_obj, status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

    try:
        workflow_info_data = {
            "workflow_name": workflow_info.workflow_name,
            "info": workflow_info.info,
            "email": current_user.email,
        }
        try:
            workflow_info_obj = upsert_workflow_info(workflow_info_data, db)
        except Exception as e:
            resp_obj["status"] = "failure"
            resp_obj["errors"] = [f"Error adding new workflow: {str(e)}"]
            return resp_obj

        workflow_steps = [step.model_dump() for step in workflow_info.steps]
        try:
            errors, step_data_list = upsert_workflow_step(
                workflow_info_obj.id, current_user.username, workflow_steps, db
            )

            if errors:
                resp_obj["status"] = "partial_success"
                resp_obj["errors"] = errors
            workflow_info_obj.steps = step_data_list
            resp_obj["data"] = step_data_list

        except Exception as e:
            resp_obj["status"] = "failure"
            resp_obj["errors"] = [f"Error adding workflow steps: {str(e)}"]

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"] = [f"Error creating workflow: {str(e)}"]

    return resp_obj


@etter_api_router.get("/get_workflows")
def get_workflows(
    request: Request,
    workflow_id: int = None,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}

    try:
        if workflow_id:
            workflows = (
                db.query(WorkflowInfo)
                .options(selectinload(WorkflowInfo.steps))
                .filter(WorkflowInfo.id == workflow_id)
                .all()
            )
        else:
            workflows = (
                db.query(WorkflowInfo).options(selectinload(WorkflowInfo.steps)).all()
            )
        if not workflows:
            resp_obj["status"] = "failure"
            resp_obj["errors"].append("No workflows found")
            return resp_obj

        workflows_data = []
        for workflow in workflows:
            workflow_dict = {
                "workflow_id": workflow.id,
                "workflow_name": workflow.workflow_name,
                "info": workflow.info,
                "steps": [],
            }

            for step in workflow.steps:
                step_dict = {
                    "step_id": step.id,
                    "step_name": step.step_name,
                    "info": step.info,
                }
                workflow_dict["steps"].append(step_dict)

            workflows_data.append(workflow_dict)

        resp_obj["data"] = workflows_data

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error fetching workflows: {str(e)}")

    return resp_obj


@etter_api_router.post("/update_user_workflow_history")
def update_user_workflow_history(
    request: Request,
    workflow_step: UpsertUserWorkflowHistory,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    resp_obj = {"status": "success", "data": None, "errors": []}

    try:
        user_history_data = {
            "workflow_name": workflow_step.workflow_name,
            "workflow_status": workflow_step.workflow_status,
            "request_id": workflow_step.request_id or str(uuid.uuid4()),
            "user_id": current_user.id,
            "user_query": workflow_step.user_query,
            "approval_status": workflow_step.approval_status,
            "approver_name": workflow_step.approver_name,
            "is_etter_generated": workflow_step.is_etter_generated or False,
            "score": workflow_step.score or 0,
            "info": workflow_step.info,
            "modeling_state": workflow_step.modeling_state or "INITIAL",
        }

        workflow_history_obj = upsert_user_workflow_history_data(
            user_history_data, current_user.username, db
        )
        workflow_history_obj.user_workflow_history_id = workflow_history_obj.id
        workflow_history_obj.approver_name = user_history_data.get("approver_name")
        del workflow_history_obj.id
        resp_obj["data"] = workflow_history_obj
    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error creating workflow step: {str(e)}")
    return resp_obj


@etter_api_router.post("/get_user_workflow_history")
def get_user_workflow_history(
    request: Request,
    filters: UserWorkflowFilters,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}

    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        base_conditions = [
            or_(
                UserWorkflowHistory.user_id == current_user.id,
                UserWorkflowHistory.approver_id == current_user.id,
            )
        ]

        if filters.workflow_status:
            base_conditions.append(
                UserWorkflowHistory.workflow_status == filters.workflow_status
            )
        if filters.approval_status:
            base_conditions.append(
                UserWorkflowHistory.approval_status == filters.approval_status
            )

        user_workflow_history = (
            db.query(UserWorkflowHistory).filter(*base_conditions).all()
        )

        pending_for_my_approval = [
            user_wf_history
            for user_wf_history in user_workflow_history
            if user_wf_history.approver_id == current_user.id
            and user_wf_history.user_id != current_user.id
        ]

        submitted_for_approval = [
            user_wf_history
            for user_wf_history in user_workflow_history
            if user_wf_history.user_id == current_user.id
        ]

        if not user_workflow_history:
            resp_obj["status"] = "failure"
            resp_obj["errors"].append(
                f"No workflow history found for user {current_user.email}"
            )
            return resp_obj

        resp_obj["data"] = {
            "pending_for_my_approval": pending_for_my_approval,
            "submitted_for_approval": submitted_for_approval,
        }

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error fetching user workflow history: {str(e)}")

    return resp_obj


@etter_api_router.post("/update_user_workflow_step_history")
def update_user_workflow_step_history(
    request: Request,
    workflow_step: UpsertUserWorkflowStepHistory,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}

    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        step_history_data = {
            "workflow_name": workflow_step.workflow_name,
            "request_id": workflow_step.request_id,
            "workflow_step_name": workflow_step.workflow_step_name,
            "data_type": workflow_step.data_type,
            "user_id": current_user.id,
            "user_query": workflow_step.user_query,
            "data": workflow_step.data,
            "workflow_step_status": workflow_step.workflow_step_status,
            "review": workflow_step.review,
            "version_id": workflow_step.version_id,
            "update_version": workflow_step.update_version,
        }

        inserted = update_user_workflow_step_history_data(step_history_data, db)

        if isinstance(inserted, list):
            resp_obj["data"] = []
            for step in inserted:
                step_data = step.__dict__
                step_data["last_modified_on"] = get_minimized_time_ago(
                    step.updated_at or step.created_at
                )
                resp_obj["data"].append(step_data)
        else:
            resp_obj["data"] = inserted.__dict__
            resp_obj["data"]["last_modified_on"] = get_minimized_time_ago(
                inserted.updated_at or inserted.created_at
            )

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error creating workflow step history: {str(e)}")

    return resp_obj


def fetch_steps_data(db, workflow_history_id):
    return [
        row.data
        for row in db.query(UserWorkflowStepsHistory.data)
        .filter(
            UserWorkflowStepsHistory.user_workflow_history_id == workflow_history_id,
            UserWorkflowStepsHistory.is_latest == True,
        )
        .order_by(UserWorkflowStepsHistory.id.asc())
        .all()
    ]


def get_etter_and_validated_data(
    db,
    user_query,
    workflow_id,
    company_id=None,
    info=None,
    etter_impact_score_id=None,
    validated_ai_impact_score_id=None,
):
    etter_workflow_data = {}
    validated_workflow_data = {}

    # etter_query = (
    #     db.query(UserWorkflowHistory.id, UserWorkflowHistory.score)
    #     .join(User, UserWorkflowHistory.user_id == User.id)
    #     .filter(UserWorkflowHistory.is_etter_generated == True)
    # )
    # if user_query != "N/A":
    #     etter_query = etter_query.filter(
    #         UserWorkflowHistory.user_query.ilike(user_query)
    #     )
    # if workflow_id:
    #     etter_query = etter_query.filter(UserWorkflowHistory.workflow_id == workflow_id)
    # if company_id:
    #     etter_query = etter_query.filter(User.company_id == company_id)
    # if etter_impact_score_id:
    #     etter_query = etter_query.filter(
    #         UserWorkflowHistory.id == etter_impact_score_id
    #     )
    #
    # etter_workflow = etter_query.first()
    #
    # if etter_workflow:
    #     steps = fetch_steps_data(db, etter_workflow.id)
    #     for step in steps:
    #         if step.get("editable"):
    #             step["editable"] = False
    #     etter_workflow_data = {"score": etter_workflow.score, "steps": steps}
    #
    # validated_query = (
    #     db.query(UserWorkflowHistory.id, UserWorkflowHistory.score)
    #     .join(User, UserWorkflowHistory.user_id == User.id)
    #     .filter(UserWorkflowHistory.approval_status == "approved")
    # )
    # if user_query != "N/A":
    #     validated_query = validated_query.filter(
    #         UserWorkflowHistory.user_query.ilike(user_query)
    #     )
    # if workflow_id:
    #     validated_query = validated_query.filter(
    #         UserWorkflowHistory.workflow_id == workflow_id
    #     )
    # if company_id:
    #     validated_query = validated_query.filter(User.company_id == company_id)
    # if validated_ai_impact_score_id:
    #     validated_query = validated_query.filter(
    #         UserWorkflowHistory.id == validated_ai_impact_score_id
    #     )
    #
    # validated_workflow = validated_query.order_by(
    #     UserWorkflowHistory.updated_at.desc()
    # ).first()
    #
    # if validated_workflow:
    #     steps = fetch_steps_data(db, validated_workflow.id)
    #     for step in steps:
    #         if step.get("editable"):
    #             step["editable"] = False
    #     validated_workflow_data = {"score": validated_workflow.score, "steps": steps}

    return etter_workflow_data, validated_workflow_data


@etter_api_router.post("/get_user_workflow_steps_history")
def get_user_workflow_steps_history(
    request: Request,
    user_workflow_steps_filter: UserWorkflowStepFilters,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    filters = []
    workflow_id = None
    company_id = current_user.company_id if current_user else None
    user_workflow_history_data = None

    if user_workflow_steps_filter.id:
        user_workflow_history_data = (
            db.query(UserWorkflowHistory)
            .filter(UserWorkflowHistory.id == user_workflow_steps_filter.id)
            .first()
        )
        if user_workflow_history_data:
            workflow_id = user_workflow_history_data.workflow_id
    else:
        if user_workflow_steps_filter.workflow_name:
            workflow_id = (
                db.query(WorkflowInfo.id)
                .filter(
                    WorkflowInfo.workflow_name == user_workflow_steps_filter.workflow_name
                )
                .scalar()
            )
            if workflow_id:
                filters.append(UserWorkflowHistory.workflow_id == workflow_id)
            else:
                return {
                    "status": "failure",
                    "errors": ["Invalid workflow_name"],
                    "data": None,
                }

        if user_workflow_steps_filter.user_query:
            filters.append(
                UserWorkflowHistory.user_query == user_workflow_steps_filter.user_query
            )

        if user_workflow_steps_filter.request_id:
            filters.append(
                UserWorkflowHistory.request_id == user_workflow_steps_filter.request_id
            )
        else:
            return {"status": "success", "errors": [], "data": None}

        if user_workflow_steps_filter.info:
            for key, value in user_workflow_steps_filter.info.items():
                if isinstance(value, list):
                    array_conditions = []
                    for item in value:
                        array_conditions.append(UserWorkflowHistory.info[key].op('?')(str(item)))
                    if array_conditions:
                        filters.append(or_(*array_conditions))
                else:
                    filters.append(UserWorkflowHistory.info[key].astext == str(value))

        user_workflow_history_data = (
            db.query(UserWorkflowHistory)
            .filter(*filters)
            .join(User, UserWorkflowHistory.user_id == User.id)
            .order_by(UserWorkflowHistory.created_at.desc())
            .first()
        )

    if not user_workflow_history_data:
        return resp_obj
    
    user_workflow_data = {}
    user_workflow_data["workflow_name"] = (
        user_workflow_history_data.workflow_info.workflow_name
        if user_workflow_history_data and user_workflow_history_data.workflow_info
        else user_workflow_steps_filter.workflow_name
    )
    user_workflow_data["workflow_info"] = user_workflow_history_data.workflow_info.info
    user_workflow_data["user_query"] = user_workflow_history_data.user_query
    user_workflow_data["request_id"] = user_workflow_history_data.request_id
    user_workflow_data["workflow_status"] = user_workflow_history_data.workflow_status
    user_workflow_data["approval_status"] = user_workflow_history_data.approval_status
    user_workflow_data["created_at"] = user_workflow_history_data.created_at
    user_workflow_data["username"] = user_workflow_history_data.user.username
    user_workflow_data["steps"] = []

    step_filters = [
        UserWorkflowStepsHistory.user_workflow_history_id
        == user_workflow_history_data.id
    ]
    if user_workflow_steps_filter.version_id:
        step_filters.append(
            UserWorkflowStepsHistory.version_id == user_workflow_steps_filter.version_id
        )
    elif not user_workflow_steps_filter.fetch_all:
        step_filters.append(UserWorkflowStepsHistory.is_latest == True)

    try:
        user_workflow_steps = (
            db.query(
                UserWorkflowStepsHistory.id.label("workflow_steps_info_id"),
                UserWorkflowStepsHistory.type,
                UserWorkflowStepsHistory.data,
                UserWorkflowStepsHistory.workflow_step_status,
                User.username.label("approver_name"),
                UserWorkflowStepsHistory.updated_at,
                UserWorkflowStepsHistory.created_at,
                UserWorkflowStepsHistory.version_id,
            )
            .filter(*step_filters)
            .join(
                UserWorkflowHistory,
                UserWorkflowStepsHistory.user_workflow_history_id
                == UserWorkflowHistory.id,
            )
            .outerjoin(User, UserWorkflowHistory.approver_id == User.id)
            .order_by(asc(UserWorkflowStepsHistory.id))
            .all()
        )

        if not user_workflow_steps:
            resp_obj["status"] = "failure"
            resp_obj["errors"].append(f"No workflow steps found for this workflow")
            return resp_obj

        steps_list = []
        last_step = None
        latest_version = 1
        for row in user_workflow_steps:
            data = row.data if row.data else {}
            data["lastModifiedOn"] = (
                get_minimized_time_ago(row.updated_at or row.created_at)
                if row.updated_at or row.created_at
                else None
            )
            data["lastModifiedOnDT"] = row.updated_at or row.created_at
            latest_version = max(latest_version, row.version_id or 1)
            step_dict = {
                "workflow_steps_info_id": row.workflow_steps_info_id,
                "type": row.type,
                "data": data,
                "workflow_step_status": row.workflow_step_status,
                "approver_name": row.approver_name,
            }
            if row.type and row.type == "data":
                last_step = row.data.get("step")
            steps_list.append(step_dict)

        user_workflow_data["steps"] = steps_list
        resp_obj["data"] = user_workflow_data

        history = {
            user_workflow_steps_filter.workflow_name: [
                item["data"] for item in steps_list
            ]
        }
        current_workflow = {
            "workflow_id": user_workflow_history_data.id,
            "workflow_name": user_workflow_data["workflow_name"],
            "approver_name": user_workflow_steps[0].approver_name
            if user_workflow_steps
            else None,
            "approval_status": user_workflow_data["approval_status"],
            "request_id": user_workflow_data["request_id"],
            "user_query": user_workflow_data["user_query"],
            "username": user_workflow_history_data.user.username,
            "version_id": latest_version,
            "modeling_state": user_workflow_history_data.modeling_state.value if user_workflow_history_data.modeling_state else "INITIAL",
        }
        etter_workflow_data, validated_workflow_data = get_etter_and_validated_data(
            db, user_workflow_steps_filter.user_query, workflow_id, company_id
        )
        resp_obj["data"] = {
            "history": history,
            "current_workflow": current_workflow,
            "etter_workflow": etter_workflow_data,
            "validated_workflow": validated_workflow_data,
            "last_step": last_step,
            "latest_version": latest_version,
        }

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error fetching user workflow history: {str(e)}")

    return resp_obj


@etter_api_router.post("/get_user_workflows_summary")
def get_user_workflows_summary(
    request: Request,
    filters: Optional[UserWorkflowHistoryFilters],
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    def parse_filter_value(model_column, value):
        if isinstance(value, str) and ";" in value:
            items = [v.strip() for v in value.split(";") if v.strip()]
            return or_(*[model_column.ilike(f"%{item}%") for item in items])
        return model_column.ilike(f"%{value}%")

    resp_obj = {"status": "success", "data": [], "errors": []}

    try:
        draup_user_data = draup_user.data

        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        query = (
            db.query(UserWorkflowHistory)
            .join(WorkflowInfo)
            .join(
                UserWorkflowHistoryStatus,
                UserWorkflowHistoryStatus.history_id == UserWorkflowHistory.id,
            )
        )

        query = query.filter(
            or_(
                UserWorkflowHistory.user_id == current_user.id,
                UserWorkflowHistory.approver_id == current_user.id,
                UserWorkflowHistoryStatus.user_id == current_user.id,
            )
        )

        if filters:
            if filters.workflow_name:
                query = query.filter(
                    parse_filter_value(
                        WorkflowInfo.workflow_name, filters.workflow_name
                    )
                )
            if filters.workflow_status:
                query = query.filter(
                    UserWorkflowHistory.workflow_status == filters.workflow_status
                )
            if filters.approval_status:
                query = query.filter(
                    parse_filter_value(
                        UserWorkflowHistory.approval_status, filters.approval_status
                    )
                )
            if filters.approver_name:
                query = query.join(User, User.id == UserWorkflowHistory.approver_id)
                query = query.filter(User.first_name.ilike(f"%{filters.approver_name}%"))
            if filters.user_query:
                query = query.filter(
                    parse_filter_value(
                        UserWorkflowHistory.user_query, filters.user_query
                    )
                )
            if filters.unread_flag is not None:
                query = query.filter(
                    UserWorkflowHistoryStatus.unread_flag == filters.unread_flag
                )

        page = (filters.page + 1) if filters and filters.page >= 0 else 1
        page_size = filters.limit if filters and filters.limit > 0 else 50
        
        query = query.options(
            joinedload(UserWorkflowHistory.workflow_info),
            joinedload(UserWorkflowHistory.approver),
            joinedload(UserWorkflowHistory.status_records),
            joinedload(UserWorkflowHistory.user),
        )
        
        query = query.order_by(UserWorkflowHistory.updated_at.desc(), UserWorkflowHistory.id.desc())
        
        paginated_result = paginate(query, page=page, page_size=page_size)
        user_workflow_histories = paginated_result.items
        history_ids = [h.id for h in user_workflow_histories]

        if not history_ids:
            return resp_obj

        steps = (
            db.query(UserWorkflowStepsHistory)
            .filter(
                UserWorkflowStepsHistory.user_workflow_history_id.in_(history_ids),
                UserWorkflowStepsHistory.is_latest == True,
            )
            .order_by(UserWorkflowStepsHistory.updated_at.desc())
            .all()
        )

        step_map = {}
        data_step_map = {}

        for step in steps:
            hid = step.user_workflow_history_id
            step_timestamp = step.updated_at

            if hid not in step_map:
                step_map[hid] = step

            if step.type == "data":
                if hid not in data_step_map or (
                    step_timestamp
                    > (data_step_map[hid].updated_at or data_step_map[hid].created_at)
                ):
                    data_step_map[hid] = step

        step_info_ids = [
            s.workflow_step_info_id
            for s in step_map.values()
            if s.workflow_step_info_id
        ]
        step_info_map = {}
        if step_info_ids:
            step_info_map = {
                s.id: s
                for s in db.query(WorkflowStepsInfo)
                .filter(WorkflowStepsInfo.id.in_(step_info_ids))
                .all()
            }

        workflow_data = []
        total_unread = 0
        for history in user_workflow_histories:
            step = step_map.get(history.id)
            data_step = data_step_map.get(history.id)
            user_status_record = next(
                (s for s in history.status_records if s.user_id == current_user.id),
                None,
            )
            other_users = [
                s.user.username
                for s in history.status_records
                if s.user_id
                not in {current_user.id, history.user_id, history.approver_id}
                and s.user is not None
            ]

            if step:
                step_last_modified = step.updated_at or step.created_at
                workflow_last_modified = history.updated_at or history.created_at
                display_last_modified = max(workflow_last_modified, step_last_modified)
            else:
                display_last_modified = history.updated_at or history.created_at

            step_name = None
            if step and step.workflow_step_info_id in step_info_map:
                step_name = step_info_map[step.workflow_step_info_id].step_name

            if filters and filters.step_name and step_name:
                if filters.step_name.lower() not in step_name.lower():
                    continue

            workflow_data.append(
                {
                    "id": history.id,
                    "workflow_name": history.workflow_info.workflow_name,
                    "workflow_status": history.workflow_status,
                    "approval_status": history.approval_status,
                    "request_id": history.request_id,
                    "user_id": history.user_id,
                    "user_query": history.user_query,
                    "approver_name": history.approver.username
                    if history.approver
                    else None,
                    "username": history.user.username if history.user else None,
                    "step_name": step_name,
                    "step_data": data_step.data if data_step else None,
                    "step_info": step.data if step else None,
                    "info": history.info,
                    "other_users": other_users,
                    "unread_flag": user_status_record.unread_flag
                    if user_status_record
                    else None,
                    "last_modified_on": get_minimized_time_ago(display_last_modified)
                    if display_last_modified
                    else None,
                    "last_modified_on_dt": display_last_modified,
                    "modeling_state": history.modeling_state.value if history.modeling_state else "INITIAL",
                }
            )
            total_unread += (
                1 if user_status_record and user_status_record.unread_flag else 0
            )

        workflow_data.sort(
            key=lambda x: (x["last_modified_on_dt"], x["id"]), reverse=True
        )

        for item in workflow_data:
            item.pop("last_modified_on_dt", None)

        resp_obj["data"] = workflow_data
        resp_obj["total_count"] = paginated_result.total
        resp_obj["total_unread"] = total_unread
        resp_obj["page"] = paginated_result.page
        resp_obj["page_size"] = paginated_result.page_size
        resp_obj["total_pages"] = paginated_result.total_pages
        resp_obj["has_next"] = paginated_result.has_next
        resp_obj["has_prev"] = paginated_result.has_prev

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(str(e))

    return resp_obj


@etter_api_router.post("/mark_user_workflow_as_seen")
def mark_user_workflow_as_seen(
    id: int, db: Session = Depends(get_db), draup_user: ResponseModel = Depends(verify_token)
):
    response = {"status": "success", "message": "", "error": None}
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        status_record = (
            db.query(UserWorkflowHistoryStatus)
            .filter(
                UserWorkflowHistoryStatus.history_id == id,
                UserWorkflowHistoryStatus.user_id == current_user.id,
            )
            .first()
        )

        if not status_record:
            response["status"] = "failure"
            response["error"] = (
                f"No workflow status found for user {current_user.id} and workflow ID {id}."
            )
        else:
            status_record.unread_flag = False
            db.commit()
            response["message"] = (
                f"Workflow ID {id} marked as seen for user {current_user.username}."
            )

    except Exception as e:
        db.rollback()
        response["status"] = "failure"
        response["error"] = str(e)

    return response


@etter_api_router.get("/get_unread_workflow_count")
def get_unread_count(
    db: Session = Depends(get_db), draup_user: ResponseModel = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        count = (
            db.query(func.count(distinct(UserWorkflowHistoryStatus.history_id)))
            .join(
                UserWorkflowHistory,
                UserWorkflowHistory.id == UserWorkflowHistoryStatus.history_id,
            )
            .filter(
                UserWorkflowHistoryStatus.user_id == current_user.id,
                UserWorkflowHistoryStatus.unread_flag == True,
                or_(
                    UserWorkflowHistory.user_id == current_user.id,
                    UserWorkflowHistory.approver_id == current_user.id,
                    UserWorkflowHistoryStatus.user_id == current_user.id,
                ),
            )
            .scalar()
        )

        return {"status": "success", "unread_count": count}
    except Exception as e:
        return {"status": "failure", "error": str(e)}


@etter_api_router.post("/auto_complete")
def auto_complete(
    input_filters: AutoCompleteFilters,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    def resolve_column(model, column_path: str):
        parts = column_path.split("__")
        attr = model
        for part in parts:
            if isinstance(attr, type):
                attr = getattr(attr, part)
            elif isinstance(attr, InstrumentedAttribute):
                try:
                    mapper = attr.property.mapper
                    attr = getattr(mapper.class_, part)
                except AttributeError:
                    attr = getattr(attr, part)
            else:
                attr = getattr(attr, part)
        return attr

    resp_obj = {"status": "success", "data": None, "errors": []}
    try:
        flag_mapper = {"Recent Searches": UserWorkflowHistory}

        flag = input_filters.flag
        key = input_filters.key
        get_columns = input_filters.getColumns
        user_input = input_filters.input
        additional_filters = input_filters.filters or []
        sort_dict = input_filters.sort_dict or {}

        if not flag or not key:
            raise ValueError(
                "Both 'flag' and 'key' must be provided for auto-complete."
            )
        if flag not in flag_mapper:
            raise ValueError(
                f"Invalid flag: {flag}. Valid flags are: {list(flag_mapper.keys())}"
            )

        model = flag_mapper[flag]
        query = db.query(model)
        filters = []

        joined_models = set()
        filter_columns = [f["column"] for f in additional_filters] + (
            [key] if key else []
        )
        sort_columns = sort_dict.get("sort_column")
        if sort_columns:
            if isinstance(sort_columns, list):
                filter_columns.extend(sort_columns)
            else:
                filter_columns.append(sort_columns)

        for col_path in filter_columns:
            if not isinstance(col_path, str):
                continue
            parts = col_path.split("__")
            if len(parts) > 1:
                joined_models.add(parts[0])

        for relation in joined_models:
            query = query.join(getattr(model, relation))

        if user_input:
            filters.append(resolve_column(model, key).ilike(f"%{user_input}%"))

        for f in additional_filters:
            column_attr = resolve_column(model, f["column"])
            condition = f["condition"]
            value = f["value"]
            if condition == "equals":
                filters.append(column_attr == value)
            elif condition == "like":
                filters.append(column_attr.ilike(f"%{value}%"))
            elif condition == "in":
                filters.append(column_attr.in_(value))
            else:
                raise ValueError(f"Unsupported condition '{condition}'")

        sort_order = sort_dict.get("sort_order", "asc")
        key_column = resolve_column(model, key)

        if get_columns:
            selected = [resolve_column(model, col) for col in get_columns]
            if sort_columns:
                if isinstance(sort_columns, list) and len(sort_columns) > 1:
                    sort_expr = func.coalesce(
                        *[resolve_column(model, col) for col in sort_columns]
                    )
                else:
                    sort_expr = resolve_column(
                        model,
                        sort_columns[0]
                        if isinstance(sort_columns, list)
                        else sort_columns,
                    )

                query = query.with_entities(*selected).filter(*filters)
                query = query.order_by(
                    sort_expr.desc() if sort_order == "desc" else sort_expr.asc()
                )
            else:
                query = query.with_entities(*selected).filter(*filters)

            query_result = query.limit(10).all()
            data = []
            for row in query_result:
                name = (
                    getattr(row, get_columns[0])
                    if hasattr(row, get_columns[0])
                    else row[0]
                )
                value = (
                    getattr(row, get_columns[1])
                    if len(get_columns) > 1 and hasattr(row, get_columns[1])
                    else row[1]
                    if len(row) > 1
                    else row[0]
                )
                data.append({"name": str(name), "value": str(value)})
        else:
            if sort_columns:
                if isinstance(sort_columns, list) and len(sort_columns) > 1:
                    sort_expr = func.coalesce(
                        *[resolve_column(model, col) for col in sort_columns]
                    )
                else:
                    sort_expr = resolve_column(
                        model,
                        sort_columns[0]
                        if isinstance(sort_columns, list)
                        else sort_columns,
                    )

                subquery = (
                    query.with_entities(
                        key_column.label("key"), sort_expr.label("sorter")
                    )
                    .filter(*filters)
                    .order_by(key_column)
                    .order_by(
                        sort_expr.desc() if sort_order == "desc" else sort_expr.asc()
                    )
                    .distinct(key_column)
                    .limit(10)
                    .subquery()
                )
                query_result = db.query(subquery.c.key).all()
                data = [
                    {"name": str(row.key), "value": str(row.key)}
                    for row in query_result
                ]
            else:
                query_result = (
                    query.with_entities(key_column)
                    .filter(*filters)
                    .distinct()
                    .limit(10)
                    .all()
                )
                data = [
                    {"name": str(row[0]), "value": str(row[0])} for row in query_result
                ]

        resp_obj["data"] = data

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"] = [f"Error: {str(e)} occurred while fetching suggestions."]
    return resp_obj


@etter_api_router.post("/fetch_autocomplete_data")
def fetch_autocomplete_data_endpoint(
    request: Request,
    autocomplete_request: FetchAutocompleteDataRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}
    try:
        data = fetch_autocomplete_data(db=db, **autocomplete_request.model_dump())

        resp_obj["data"] = data

    except ValueError as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(str(e))
    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error fetching autocomplete data: {str(e)}")

    return resp_obj


@etter_api_router.post("/refresh_task_autocomplete")
def refresh_task_autocomplete(
    request: Request,
    refresh_request: RefreshTaskAutocompleteRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    """
    Manually refresh task autocomplete cache for a specific company+role combination.
    This will fetch ALL tasks from role_assessment_data and update the cache.
    """
    from services.task_autocomplete_service import refresh_task_autocomplete_cache

    resp_obj = {"status": "success", "data": None, "errors": []}
    try:
        result = refresh_task_autocomplete_cache(
            db=db,
            company=refresh_request.company,
            role=refresh_request.role,
            is_autocomplete=True
        )

        if result.get('status') == 'error':
            resp_obj["status"] = "failure"
            resp_obj["errors"].append(result.get('error', 'Unknown error'))
        else:
            resp_obj["data"] = result

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error refreshing task cache: {str(e)}")

    return resp_obj


@etter_api_router.post("/refresh_all_task_autocomplete")
def refresh_all_task_autocomplete(
    request: Request,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    """
    Refresh task autocomplete cache for ALL known company+role combinations.
    This is used by the daily scheduled job.
    WARNING: This may take a while depending on the number of combinations.
    """
    from services.task_autocomplete_service import refresh_all_task_autocomplete_cache

    resp_obj = {"status": "success", "data": None, "errors": []}
    try:
        result = refresh_all_task_autocomplete_cache(db=db)
        resp_obj["data"] = result

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error in batch refresh: {str(e)}")

    return resp_obj

@etter_api_router.post("/check_and_update_workflow_step_versions")
def check_and_update_workflow_step_versions(
    request: Request,
    user_workflow_steps_filter: UserWorkflowStepFilters,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}
    try:
        draup_user_data = draup_user.get("data")
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        company_id = current_user.company_id if current_user else None
        user_query = user_workflow_steps_filter.user_query
        fetch_CHRO = user_workflow_steps_filter.fetch_CHRO
        workflow_name = user_workflow_steps_filter.workflow_name
        info = user_workflow_steps_filter.info
        etter_impact_score_id = user_workflow_steps_filter.etter_impact_score_id
        validated_ai_impact_score_id = (
            user_workflow_steps_filter.validated_ai_impact_score_id
        )

        if not etter_impact_score_id and not validated_ai_impact_score_id:
            if not user_query or not workflow_name:
                resp_obj["status"] = "failure"
                resp_obj["errors"].append(
                    "Job Role and Workflow Name are required when no IDs are provided."
                )
                return resp_obj
        else:
            if not user_query:
                user_query = "N/A"
            if not workflow_name:
                workflow_name = "N/A"

        workflow_id = None
        if workflow_name != "N/A":
            workflow_id = (
                db.query(WorkflowInfo.id)
                .filter(WorkflowInfo.workflow_name == workflow_name)
                .scalar()
            )
            if not workflow_id:
                resp_obj["status"] = "failure"
                resp_obj["errors"].append(f"Workflow '{workflow_name}' not found.")
                return resp_obj
        etter_workflow_data, validated_workflow_data = get_etter_and_validated_data(
            db,
            user_query,
            workflow_id,
            company_id,
            info=info,
            etter_impact_score_id=user_workflow_steps_filter.etter_impact_score_id,
            validated_ai_impact_score_id=user_workflow_steps_filter.validated_ai_impact_score_id,
        )

        if not workflow_id and (etter_impact_score_id or validated_ai_impact_score_id):
            if etter_workflow_data.get("steps"):
                workflow_id = (
                    db.query(UserWorkflowHistory.workflow_id)
                    .filter(
                        UserWorkflowHistory.id
                        == user_workflow_steps_filter.etter_impact_score_id
                    )
                    .scalar()
                )
            elif validated_workflow_data.get("steps"):
                workflow_id = (
                    db.query(UserWorkflowHistory.workflow_id)
                    .filter(
                        UserWorkflowHistory.id
                        == user_workflow_steps_filter.validated_ai_impact_score_id
                    )
                    .scalar()
                )

        if fetch_CHRO:
            resp_obj["data"] = {
                "etter_workflow": etter_workflow_data,
                "validated_workflow": validated_workflow_data,
            }
            return resp_obj
        is_data_not_present = etter_workflow_data.get(
            "steps"
        ) or validated_workflow_data.get("steps")
        if not is_data_not_present:
            resp_obj["data"] = {"is_data_not_present": True}
            return resp_obj

        filters = [
            UserWorkflowHistory.user_id == current_user.id,
            ~UserWorkflowHistory.approval_status.in_(["approved", "rejected"]),
        ]
        if user_query != "N/A":
            filters.append(UserWorkflowHistory.user_query.ilike(user_query))
        if workflow_id:
            filters.append(UserWorkflowHistory.workflow_id == workflow_id)

        if info:
            for key, value in info.items():
                if isinstance(value, list):
                    array_conditions = []
                    for item in value:
                        array_conditions.append(UserWorkflowHistory.info[key].op('?')(str(item)))
                    if array_conditions:
                        filters.append(or_(*array_conditions))
                else:
                    filters.append(UserWorkflowHistory.info[key].astext == str(value))

        user_workflow_history = db.query(UserWorkflowHistory).filter(*filters).first()

        if not user_workflow_history:
            source_workflow = validated_workflow_data or etter_workflow_data
            if not source_workflow:
                resp_obj["status"] = "failure"
                resp_obj["errors"].append(
                    "No validated or ETTER workflow found to replicate."
                )
                return resp_obj

            if not workflow_id:
                resp_obj["status"] = "failure"
                resp_obj["errors"].append(
                    "Workflow ID is required to create a new workflow."
                )
                return resp_obj

            new_workflow = UserWorkflowHistory(
                request_id=str(uuid.uuid4()),
                workflow_id=workflow_id,
                user_query=user_query if user_query != "N/A" else "",
                user_id=current_user.id,
                workflow_status="pending",
                approval_status="pending",
                approver_id=None,
                is_etter_generated=False,
                score=source_workflow["score"],
                info=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            ensure_status_record(db, current_user.id, new_workflow)
            db.add(new_workflow)
            db.flush()
            get_all_workflow_steps = (
                db.query(WorkflowStepsInfo)
                .filter(WorkflowStepsInfo.workflow_id == workflow_id)
                .all()
            )
            steps_id_mapper = {
                step.step_name: step.id for step in get_all_workflow_steps
            }
            new_steps = []
            for step_data in source_workflow["steps"]:
                if step_data.get("type") == "data":
                    if step_data.get("versionId") is not None:
                        step_data["versionId"] = 1
                    new_step = UserWorkflowStepsHistory(
                        type="data",
                        version_id=1,
                        user_workflow_history_id=new_workflow.id,
                        workflow_step_info_id=steps_id_mapper.get(
                            step_data.get("step", "")
                        ),
                        workflow_step_status={"completed": str(datetime.utcnow())},
                        data=step_data,
                        review="",
                        is_latest=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    new_steps.append(new_step)
            db.add_all(new_steps)
            db.commit()

            user_workflow_history_dict = {
                "score": new_workflow.score,
                "steps": [steps.data for steps in new_steps if steps.data],
                "approver_name": None,
                "approval_status": new_workflow.approval_status,
                "request_id": new_workflow.request_id,
            }
        else:
            user_workflow_history_dict = {
                "score": user_workflow_history.score,
                "steps": fetch_steps_data(db, user_workflow_history.id),
                "approver_name": user_workflow_history.approver.username
                if user_workflow_history.approver
                else None,
                "approval_status": user_workflow_history.approval_status,
                "request_id": user_workflow_history.request_id,
            }
        latest_version = 1
        if user_workflow_history_dict.get("steps"):
            latest_version = max(
                step.get("versionId", 1)
                for step in user_workflow_history_dict["steps"]
                if step.get("versionId") is not None
            )
        resp_obj["data"] = {
            "etter_workflow": etter_workflow_data,
            "validated_workflow": validated_workflow_data,
            "history": {
                workflow_name
                if workflow_name != "N/A"
                else "Unknown": user_workflow_history_dict["steps"]
            },
            "latest_version": latest_version,
            "current_workflow": {
                "workflow_name": workflow_name if workflow_name != "N/A" else "Unknown",
                "approver_name": user_workflow_history_dict["approver_name"],
                "approval_status": user_workflow_history_dict["approval_status"],
                "request_id": user_workflow_history_dict["request_id"],
                "user_query": user_query if user_query != "N/A" else "Unknown",
                "username": current_user.username,
                "version_id": latest_version,
            },
        }

        return resp_obj

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error updating workflow step versions: {str(e)}")

    return resp_obj


@etter_api_router.get("/proxy_image")
def proxy_image(
    draup_user: ResponseModel = Depends(verify_token),
    url: str = "",
):
    try:
        if not url:
            return JSONResponse(status_code=400, content={"error": "URL is required"})
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return JSONResponse(
                status_code=400, content={"error": "Failed to fetch image"}
            )
        content_type = resp.headers.get("Content-Type", "image/png")
        b64_img = base64.b64encode(resp.content).decode("utf-8")
        return {"base64_image": f"data:{content_type};base64,{b64_img}"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@etter_api_router.get("/fetch_master_company_data")
def fetch_master_company_data(
    search_string: Optional[str] = None,
    search_company_name_only: bool = False,
    limit: int = 10,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}

    try:
        data = fetchMasterCompanyData(
            db, search_string, search_company_name_only, limit
        )
        resp_obj["data"] = data

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error fetching master company data: {str(e)}")

    return resp_obj


@etter_api_router.get("/fetch_master_function_data")
def fetch_master_function_data(
    search_string: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}

    try:
        data = fetchMasterFunctionData(
            db, search_string, limit
        )
        resp_obj["data"] = data

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error fetching master function data: {str(e)}")

    return resp_obj


@etter_api_router.post("/fetch_table_data")
def fetch_table_data(
    request: TableDataRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}

    try:
        model_mapping = {"MasterCompany": MasterCompany}

        if request.table_name not in model_mapping:
            resp_obj["status"] = "failure"
            resp_obj["errors"].append(f"Table '{request.table_name}' not supported")
            return resp_obj

        model_class = model_mapping[request.table_name]
        data = fetchTableData(
            db=db,
            model_class=model_class,
            columns_to_fetch=request.columns_to_fetch,
            filter_column=request.filter_column,
            filter_value=request.filter_value,
            order_by_column=request.order_by_column,
            order_direction=request.order_direction,
            limit=request.limit,
        )

        resp_obj["data"] = data

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error fetching table data: {str(e)}")

    return resp_obj


@etter_api_router.patch("/update_modeling_state/{workflow_history_id}")
def update_modeling_state(
    request: Request,
    workflow_history_id: int,
    modeling_state: str,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    resp_obj = {"status": "success", "data": None, "errors": []}

    try:
        valid_states = ["INITIAL", "IN_REVIEW", "FINAL"]
        if modeling_state not in valid_states:
            resp_obj["status"] = "failure"
            resp_obj["errors"].append(f"Invalid modeling_state. Must be one of: {', '.join(valid_states)}")
            return resp_obj

        workflow_history = db.query(UserWorkflowHistory).filter(
            UserWorkflowHistory.id == workflow_history_id
        ).first()

        if not workflow_history:
            resp_obj["status"] = "failure"
            resp_obj["errors"].append(f"Workflow history with ID {workflow_history_id} not found")
            return resp_obj

        if workflow_history.user_id != current_user.id and workflow_history.approver_id != current_user.id:
            resp_obj["status"] = "failure"
            resp_obj["errors"].append("You don't have permission to update this workflow history")
            return resp_obj

        from models.etter import ModelingState
        workflow_history.modeling_state = ModelingState(modeling_state)
        workflow_history.updated_at = datetime.now()
        
        db.commit()
        db.refresh(workflow_history)

        resp_obj["data"] = {
            "id": workflow_history.id,
            "modeling_state": workflow_history.modeling_state.value,
            "updated_at": workflow_history.updated_at
        }

    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error updating modeling state: {str(e)}")

    return resp_obj


@etter_api_router.post("/workflow_builder/workflows/process_complete", status_code=status.HTTP_200_OK)
def process_workflow_builder(
    data: WorkflowBuilderProcessRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}
    token = get_token()
    if not token:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("Failed to obtain auth token")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=resp_obj)
    target_url = f"{get_draup_world_api()}/workflow_builder/workflows/process_complete"
    headers = {
        "Authorization": f"Token {token}",
        "content-type": "application/json"
    }
    try:
        remote_response = requests.post(target_url, headers=headers, json=data.model_dump())
    except Exception as exc:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Upstream request failed: {str(exc)}")
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=resp_obj)
    if remote_response.status_code != status.HTTP_200_OK:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(remote_response.text or "Upstream error")
        return JSONResponse(status_code=remote_response.status_code, content=resp_obj)
    try:
        remote_data = remote_response.json()
    except ValueError:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("Invalid JSON from upstream service")
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=resp_obj)
    api_format = remote_data.get("api_format")
    if not isinstance(api_format, dict):
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("api_format missing in upstream response")
        resp_obj["data"] = remote_data
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=resp_obj)
    
    try:
        sub_level_func = data.sub_level_func
        high_level_func = data.high_level_func
        
        if not sub_level_func or not high_level_func:
            resp_obj["status"] = "failure"
            resp_obj["errors"].append("sub_level_func and high_level_func are required")
            resp_obj["data"] = remote_data
            return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=resp_obj)
        
        api_format["company_name"] = data.company_name
        api_format["function_areas"] = [
            {
                "high_level_func": high_level_func,
                "sub_level_func": sub_level_func,
                "workflows": api_format["function_areas"][0].get('workflows')
            }
        ]
        comprehensive_payload = ComprehensiveFunctionWorkflowCreate.model_validate(api_format)
    except ValidationError as exc:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(str(exc))
        resp_obj["data"] = remote_data
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=resp_obj)
    except KeyError as exc:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Missing required field in api_format: {str(exc)}")
        resp_obj["data"] = remote_data
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=resp_obj)
    
    try:
        creation_result = create_comprehensive_workflow(comprehensive_payload, db, draup_user)
        return creation_result
    except HTTPException as exc:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(exc.detail)
        return JSONResponse(status_code=exc.status_code, content=resp_obj)
    except Exception as exc:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error creating comprehensive workflow: {str(exc)}")
        logger.error(f"Error in process_workflow_builder: {str(exc)}", exc_info=True)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=resp_obj)


@etter_api_router.post("/workflow_builder/workflows/enrich_tasks", status_code=status.HTTP_200_OK)
def enrich_tasks(
    data: EnrichTasksRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}
    
    token = get_token()
    if not token:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("Failed to obtain auth token")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=resp_obj)
    
    target_url = f"{get_draup_world_api()}/workflow_builder/workflows/enrich_tasks"
    headers = {
        "Authorization": f"Token {token}",
        "content-type": "application/json"
    }
    
    try:
        remote_response = requests.post(target_url, headers=headers, json=data.model_dump())
    except Exception as exc:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Upstream request failed: {str(exc)}")
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=resp_obj)
    
    if remote_response.status_code != status.HTTP_200_OK:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(remote_response.text or "Upstream error")
        return JSONResponse(status_code=remote_response.status_code, content=resp_obj)
    
    try:
        enrich_response = remote_response.json()
    except ValueError:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("Invalid JSON from upstream service")
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=resp_obj)
    
    if enrich_response.get("status") != "success":
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("Enrichment failed")
        resp_obj["data"] = enrich_response
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=resp_obj)
    
    enriched_tasks = enrich_response.get("enriched_tasks", [])
    if not enriched_tasks:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("No enriched tasks returned")
        resp_obj["data"] = enrich_response
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=resp_obj)
    
    company = db.query(MasterCompany).filter(
        MasterCompany.company_name == data.company_name
    ).first()
    
    if not company:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Company '{data.company_name}' not found")
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=resp_obj)
    
    master_function = db.query(MasterFunction).filter(
        MasterFunction.sub_level_func == data.business_function
    ).first()
    
    if not master_function:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"MasterFunction with high_level_func '{data.business_function}' not found")
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=resp_obj)
    
    function = db.query(Function).filter(
        Function.master_function_id == master_function.id,
        Function.company_id == company.id
    ).first()
    
    if not function:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Function with sub_level_func '{data.business_function}' not found for company '{data.company_name}'")
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=resp_obj)
    
    workflow = db.query(FunctionWorkflow).filter(
        FunctionWorkflow.workflow_name == data.workflow_name,
        FunctionWorkflow.function_id == function.id
    ).first()
    
    if not workflow:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Workflow '{data.workflow_name}' not found for function '{data.business_function}'")
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=resp_obj)
    
    tasks_to_upsert = []
    for enriched_task in enriched_tasks:
        automation_priority = None
        automation_type = enriched_task.get("automation_type")
        if automation_type:
            automation_priority = automation_type
        
        task_create = TaskCreate(
            task_name=enriched_task.get("task_name", ""),
            description=enriched_task.get("description"),
            impact_score=enriched_task.get("impact_score"),
            skills_required=enriched_task.get("skills_required"),
            sequence_number=enriched_task.get("sequence_number"),
            dependencies=enriched_task.get("dependencies"),
            workflow_id=workflow.id,
            automation_priority=automation_priority,
            score_breakdown={
                "classification_confidence": enriched_task.get("classification_confidence"),
                "classification_rationale": enriched_task.get("classification_rationale"),
                "calculated_fields": enriched_task.get("calculated_fields", [])
            } if enriched_task.get("classification_confidence") or enriched_task.get("classification_rationale") else None
        )
        tasks_to_upsert.append(task_create)
    
    try:
        bulk_result = bulk_upsert_tasks(tasks_to_upsert, db, draup_user)
        
        input_task_names = {task.task_name for task in data.tasks if task.task_name}
        
        existing_tasks = db.query(WorkflowTask).filter(
            WorkflowTask.workflow_id == workflow.id
        ).all()
        
        tasks_to_delete = [
            task for task in existing_tasks 
            if task.task_name not in input_task_names
        ]
        
        deleted_count = 0
        for task in tasks_to_delete:
            db.delete(task)
            deleted_count += 1
        
        if deleted_count > 0:
            db.commit()
        
        resp_obj["data"] = {
            "enrichment_response": enrich_response,
            "bulk_upsert_result": bulk_result,
            "deleted_tasks_count": deleted_count
        }
    except HTTPException as http_exc:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error upserting tasks: {http_exc.detail}")
        resp_obj["data"] = {
            "enrichment_response": enrich_response
        }
        return JSONResponse(status_code=http_exc.status_code, content=resp_obj)
    except Exception as exc:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error upserting tasks: {str(exc)}")
        resp_obj["data"] = {
            "enrichment_response": enrich_response
        }
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=resp_obj)
    
    return resp_obj


@etter_api_router.post("/workflow_builder/workflows/recalculate_score", status_code=status.HTTP_200_OK)
def recalculate_score(
    data: RecalculateScoreRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}
    
    token = get_token()
    if not token:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("Failed to obtain auth token")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=resp_obj)
    
    target_url = f"{get_draup_world_api()}/workflow_builder/workflows/recalculate_score"
    headers = {
        "Authorization": f"Token {token}",
        "content-type": "application/json"
    }
    
    try:
        remote_response = requests.post(target_url, headers=headers, json=data.model_dump())
    except Exception as exc:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Upstream request failed: {str(exc)}")
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=resp_obj)
    
    if remote_response.status_code != status.HTTP_200_OK:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(remote_response.text or "Upstream error")
        return JSONResponse(status_code=remote_response.status_code, content=resp_obj)
    
    try:
        recalc_response = remote_response.json()
    except ValueError:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("Invalid JSON from upstream service")
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=resp_obj)
    
    if recalc_response.get("status") != "success":
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("Score recalculation failed")
        resp_obj["data"] = recalc_response
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=resp_obj)
    
    workflow_score = recalc_response.get("workflow_score", {})
    ai_optimization_score = workflow_score.get("ai_optimization_score")
    
    if ai_optimization_score is None:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("ai_optimization_score missing in response")
        resp_obj["data"] = recalc_response
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=resp_obj)
    
    company = db.query(MasterCompany).filter(
        MasterCompany.company_name == data.company_name
    ).first()
    
    if not company:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Company '{data.company_name}' not found")
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=resp_obj)
    
    master_function = db.query(MasterFunction).filter(
        MasterFunction.sub_level_func == data.business_function
    ).first()
    
    if not master_function:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"MasterFunction with sub_level_func '{data.business_function}' not found")
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=resp_obj)
    
    function = db.query(Function).filter(
        Function.master_function_id == master_function.id,
        Function.company_id == company.id
    ).first()
    
    if not function:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Function with high_level_func '{data.business_function}' not found for company '{data.company_name}'")
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=resp_obj)
    
    workflow = db.query(FunctionWorkflow).filter(
        FunctionWorkflow.workflow_name == data.workflow_name,
        FunctionWorkflow.function_id == function.id
    ).first()
    
    if not workflow:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Workflow '{data.workflow_name}' not found for function '{data.business_function}'")
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=resp_obj)
    
    try:
        workflow.score = ai_optimization_score * 100
        db.commit()
        db.refresh(workflow)
        
        resp_obj["data"] = recalc_response
    except Exception as exc:
        db.rollback()
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error updating workflow score: {str(exc)}")
        resp_obj["data"] = recalc_response
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=resp_obj)
    
    return resp_obj


@etter_api_router.post("/get_workflows")
async def get_workflows(
    request: Request
):
    try:
        target_url = f"{get_draup_world_api()}/workflows"
        token = get_token()
        if not token:
            return JSONResponse(status_code=500, content={"error": "Failed to obtain auth token"})

        headers = {}
        headers["Authorization"] = f"Token {token}"
        headers["content-type"] = "application/json"
        body = await request.body()

        resp = requests.post(target_url, headers=headers, json=json.loads(body.decode()))

        if resp.status_code == 200:
            return JSONResponse(status_code=200, content=resp.json())
        else:
            return JSONResponse(status_code=resp.status_code, content={"error": resp.text})
    except Exception as e:
        logger.error(f"Error updating modeling state: {e}")


@etter_api_router.post("/detect_intent")
async def detect_intent(request: Request):
    try:
        target_url = f"{get_draup_world_api()}/detect_intent"
        token = get_token()
        if not token:
            return JSONResponse(
                status_code=500, content={"error": "Failed to obtain auth token"}
            )

        # headers = dict(request.headers)
        headers = {}
        headers["Authorization"] = f"Token {token}"
        headers["content-type"] = "application/json"
        body = await request.body()

        resp = requests.post(target_url, headers=headers, json=json.loads(body.decode()))

        if resp.status_code == 200:
            res = resp.json()
            return JSONResponse(status_code=200, content=res)
        else:
            return JSONResponse(status_code=resp.status_code, content={"error": resp.text})
    except Exception as e:
        logger.error(f"Error updating modeling state: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Internal server error"}
        )


@etter_api_router.post("/autocomplete/contextual")
async def autocomplete_contextual(request: Request):
    try:
        target_url = f"{get_draup_world_api()}/autocomplete/contextual"
        token = get_token()
        if not token:
            return JSONResponse(
                status_code=500, content={"error": "Failed to obtain auth token"}
            )

        headers = {}
        headers["Authorization"] = f"Token {token}"
        headers["content-type"] = "application/json"
        body = await request.body()

        resp = requests.post(target_url, headers=headers, json=json.loads(body.decode()))

        if resp.status_code == 200:
            res = resp.json()
            return JSONResponse(status_code=200, content=res)
        else:
            return JSONResponse(status_code=resp.status_code, content={"error": resp.text})
    except Exception as e:
        logger.error(f"Error in autocomplete contextual: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Internal server error"}
        )


@etter_api_router.api_route("/query", methods=["POST"])
async def proxy(request: Request):
    """
    Proxy all requests to the Flask backend and stream responses back to the frontend.
    Uses direct response streaming without any manipulation.
    """
    target_url = f"{get_draup_world_api()}/query"

    # Get auth token
    token = get_token()
    if not token:
        return JSONResponse(status_code=500, content={"error": "Failed to obtain auth token"})

    # Prepare headers
    headers = {
        "Authorization": f"Token {token}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json"
    }

    try:
        body = await request.body()
    except Exception as exc:
        logger.error(f"Failed to read request body: {exc}")
        return JSONResponse(status_code=400, content={"error": "Invalid request body"})

    try:
        # Use requests for initial connection to handle redirects
        response = requests.post(
            target_url,
            data=body,
            headers=headers,
            params=request.query_params,
            stream=True
        )

        if not response.ok:
            return JSONResponse(
                status_code=response.status_code,
                content={"error": "Upstream server error", "details": response.text}
            )

        async def event_stream():
            try:
                # Stream directly from requests response
                for chunk in response.iter_content(chunk_size=None):
                    if chunk:
                        yield chunk
            except Exception as exc:
                logger.error(f"Streaming error: {exc}")
                error_msg = b'data: {"error": "Stream interrupted"}\n\n'
                yield error_msg
            finally:
                response.close()

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as exc:
        logger.error(f"Proxy error: {exc}")
        return JSONResponse(status_code=502, content={"error": "Proxy error"})


@etter_api_router.post("/report-error")
async def report_error(
    request: Request,
    error_data: dict
):
    """
    Handle error reports from frontend with user feedback.
    """
    try:
        error_report = {
            "timestamp": error_data.get("timestamp"),
            "error_message": error_data.get("error_message"),
            "error_details": error_data.get("error_details"),
            "error_stack": error_data.get("error_stack"),
            "browser_info": error_data.get("user_agent"),
            "page_url": error_data.get("url"),
            "status": "pending",
            "additional_info": error_data.get("additional_info"),
        }

        logger.error(f"Frontend Error Report: {json.dumps(error_report, default=str)}")

        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #d32f2f;">⚠️ Frontend Error Report</h2>

            <h3 style="color: #666;">Error Details</h3>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 4px; margin: 10px 0;">
                <p><strong>Message:</strong> {error_report["error_message"]}</p>
                <p><strong>Details:</strong> {error_report["error_details"]}</p>
                <p><strong>Time:</strong> {error_report["timestamp"]}</p>
            </div>

            <h3 style="color: #666;">Stack Trace</h3>
            <pre style="background-color: #f5f5f5; padding: 15px; border-radius: 4px; overflow-x: auto; white-space: pre-wrap;">
{error_report["error_stack"]}
            </pre>

            <h3 style="color: #666;">Environment Information</h3>
            <ul style="list-style-type: none; padding-left: 0;">
                <li><strong>Page URL:</strong> {error_report["page_url"]}</li>
                <li><strong>Browser Info:</strong> {error_report["browser_info"]}</li>
            </ul>

            {f'<h3 style="color: #666;">Additional Information</h3><p>{error_report["additional_info"]}</p>' if error_report["additional_info"] else ''}

            <p style="color: #666; font-size: 12px; margin-top: 20px;">
                This is an automated error report. Please investigate and take necessary action.
            </p>
        </body>
        </html>
        """

        try:
            send_mail_through_draup_services(
                subject=f"Frontend Error Report - {error_report['error_message'][:50]}...",
                body=email_body,
                recipients_list=["chandankumar@draup.com",
                                 "abdalpasha@draup.com",
                                 "jayaprakash@draup.com",
                                 "sai.rahul@draup.com",
                                 "eash.vrudhula@draup.com",
                                 "abhay.vashist@draup.com"],
                cc_list=None,
                attachments_list=None
            )
        except Exception as mail_exc:
            logger.error(f"Failed to send error report email: {mail_exc}")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Error report submitted successfully"
            }
        )
    except Exception as exc:
        logger.error(f"Error reporting failed: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Failed to submit error report"
            }
        )


@etter_api_router.patch("/update-researcher")
def update_researcher(
    workflow_history_id: int,
    username: str,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    """
    Update the researcher (user_id) for a UserWorkflowHistory record by username.
    """
    resp_obj = {"status": "success", "data": None, "errors": []}
    
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        new_researcher = db.query(User).filter(User.username == username).first()
        if not new_researcher:
            resp_obj["status"] = "failure"
            resp_obj["errors"].append(f"User with username '{username}' not found")
            return resp_obj
        
        workflow_history = db.query(UserWorkflowHistory).filter(
            UserWorkflowHistory.id == workflow_history_id
        ).first()
        
        if not workflow_history:
            resp_obj["status"] = "failure"
            resp_obj["errors"].append(f"UserWorkflowHistory with ID {workflow_history_id} not found")
            return resp_obj
        
        old_user_id = workflow_history.user_id
        workflow_history.user_id = new_researcher.id
        workflow_history.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(workflow_history)
        
        resp_obj["data"] = {
            "workflow_history_id": workflow_history.id,
            "old_user_id": old_user_id,
            "new_user_id": new_researcher.id,
            "new_username": new_researcher.username,
            "updated_at": workflow_history.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error updating researcher: {str(e)}")
    
    return resp_obj


@etter_api_router.api_route("/draup_world/{endpoint_path:path}", methods=["GET", "POST"], status_code=status.HTTP_200_OK)
async def dynamic_proxy_draup_world(
    endpoint_path: str,
    request: Request,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    """
    Dynamic proxy endpoint for any get_draup_world_api() endpoint.
    This allows calling any endpoint on the Draup World API without creating individual endpoints.
    Supports both GET and POST methods.
    
    Usage:
    - POST /api/etter/draup_world/workflow_builder/workflows/process_complete
      Body: {"endpoint_path": "workflow_builder/workflows/process_complete", "payload": {...}, "method": "POST"}
    - GET /api/etter/draup_world/get_workflows?param1=value1
      (endpoint_path from URL, query params passed through)
    - POST /api/etter/draup_world/detect_intent
      Body: {"endpoint_path": "detect_intent", "payload": {...}, "method": "POST"}
    
    For POST: If DynamicProxyRequest is provided in body, it will be used. Otherwise, the endpoint_path 
    from URL and request body will be forwarded as payload.
    For GET: endpoint_path from URL is used, and query params are passed through.
    """
    resp_obj = {"status": "success", "data": None, "errors": []}
    
    token = get_token()
    if not token:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("Failed to obtain auth token")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=resp_obj)
    
    # Get request method
    method = request.method.upper()
    
    # Validate method
    if method not in ["GET", "POST"]:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Method '{method}' not supported. Only GET and POST are allowed.")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=resp_obj)
    
    # Determine endpoint path, method override, and payload
    payload = {}
    method_override = method
    
    if method == "POST":
        # For POST, try to parse body as DynamicProxyRequest
        try:
            body = await request.body()
            if body:
                body_data = json.loads(body.decode())
                # Check if it's a DynamicProxyRequest format
                if isinstance(body_data, dict) and "endpoint_path" in body_data:
                    # Use DynamicProxyRequest
                    try:
                        proxy_request = DynamicProxyRequest.model_validate(body_data)
                        endpoint_path = proxy_request.endpoint_path
                        method_override = (proxy_request.method or method).upper()
                        payload = proxy_request.payload or {}
                    except ValidationError:
                        # If validation fails, treat as regular payload
                        payload = body_data
                else:
                    # Regular payload
                    payload = body_data
        except json.JSONDecodeError:
            resp_obj["status"] = "failure"
            resp_obj["errors"].append("Invalid JSON in request body")
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=resp_obj)
        except Exception as exc:
            resp_obj["status"] = "failure"
            resp_obj["errors"].append(f"Error reading request body: {str(exc)}")
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=resp_obj)
    
    # Validate method override
    if method_override not in ["GET", "POST"]:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Method '{method_override}' not supported. Only GET and POST are allowed.")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=resp_obj)
    
    # Clean the endpoint path (remove leading/trailing slashes)
    endpoint_path = endpoint_path.strip("/")
    
    # Validate endpoint path
    if not endpoint_path:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append("endpoint_path cannot be empty")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=resp_obj)
    
    # Build the target URL
    target_url = f"{get_draup_world_api()}/{endpoint_path}"
    
    # Prepare headers
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }
    
    # Merge query params from request URL
    query_params = dict(request.query_params)
    
    # Make the request to the upstream service
    # Maximum timeout: 5 minutes (300 seconds)
    request_timeout = 300
    try:
        if method_override == "GET":
            # For GET, payload goes as query parameters
            if payload:
                query_params.update(payload)
            remote_response = requests.get(
                target_url,
                headers=headers,
                params=query_params,
                timeout=request_timeout
            )
        else:  # POST
            # For POST, payload goes in JSON body
            remote_response = requests.post(
                target_url,
                headers=headers,
                json=payload,
                params=query_params,
                timeout=request_timeout
            )
    except requests.exceptions.Timeout:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Request to upstream service timed out after {request_timeout} seconds (5 minutes)")
        return JSONResponse(status_code=status.HTTP_504_GATEWAY_TIMEOUT, content=resp_obj)
    except Exception as exc:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Upstream request failed: {str(exc)}")
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=resp_obj)
    
    # Handle response
    try:
        if remote_response.headers.get("Content-Type", "").startswith("application/json"):
            remote_data = remote_response.json()
            resp_obj["data"] = remote_data
        else:
            # For non-JSON responses, return the text
            resp_obj["data"] = {"response_text": remote_response.text}
        
        # Return the same status code as the upstream service
        return JSONResponse(
            status_code=remote_response.status_code,
            content=resp_obj
        )
    except ValueError:
        # If response is not JSON, return as text
        resp_obj["data"] = {"response_text": remote_response.text}
        return JSONResponse(
            status_code=remote_response.status_code,
            content=resp_obj
        )


def get_token():
    try:
        target_url = f"{get_draup_world_api()}/login"
        payload = {
            "username": DRAUP_WORLD_USERNAME,
            "password": DRAUP_WORLD_PASSWORD
        }
        headers = {
            'Content-Type': 'application/json'
        }
        resp = requests.post(target_url, headers=headers, json=payload)
        if resp.status_code == 200:
            resp_json = resp.json()
            return resp_json.get("token")
        else:
            logger.error(f"Failed to get token, status code: {resp.status_code}, response: {resp.text}")
    except Exception as e:
        logger.error(f"Error in getting token: {e}")

    return None


@etter_api_router.get("/sample_data")
def get_sample_data_endpoint(
    title: Optional[str] = None,
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}
    try:
        results = get_sample_data(db=db, title=title, role=role)
        resp_obj["data"] = [
            {
                "id": item.id,
                "title": item.title,
                "is_global": item.is_global,
                "role": item.role,
                "data": item.data,
                "company_id": item.company_id,
                "updated_on": item.updated_on,
            }
            for item in results
        ]
    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error fetching sample data: {str(e)}")
    
    return resp_obj


@etter_api_router.post("/sample_data/bulk_upsert")
def bulk_upsert_sample_data_endpoint(
    request: SampleDataBulkUpsertRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}
    try:
        items = [item.model_dump() for item in request.items]
        results = bulk_upsert_sample_data(db=db, items=items)
        resp_obj["data"] = [
            {
                "id": item.id,
                "title": item.title,
                "is_global": item.is_global,
                "role": item.role,
                "data": item.data,
                "company_id": item.company_id,
                "updated_on": item.updated_on,
            }
            for item in results
        ]
    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error upserting sample data: {str(e)}")
    
    return resp_obj


@etter_api_router.post("/sample_data/check_titles")
def check_titles_availability_endpoint(
    request: SampleDataTitleCheckRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}
    try:
        result = check_titles_availability(
            db=db,
            titles=request.titles,
            company_id=request.company_id
        )
        resp_obj["data"] = result
    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error checking titles availability: {str(e)}")
    
    return resp_obj

@etter_api_router.delete("/sample_data/{sample_data_id}")
def delete_sample_data_endpoint(
    sample_data_id: int,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = {"status": "success", "data": None, "errors": []}
    try:
        deleted = delete_sample_data_by_id(db=db, sample_data_id=sample_data_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample data not found")
    except HTTPException:
        raise
    except Exception as e:
        resp_obj["status"] = "failure"
        resp_obj["errors"].append(f"Error deleting sample data: {str(e)}")
    return resp_obj

