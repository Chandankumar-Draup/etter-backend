from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, delete, func
from sqlalchemy.exc import IntegrityError, DataError
from datetime import datetime
from typing import List, Optional
from pydantic import ValidationError

from settings.database import get_db
from services.auth import verify_token, ResponseModel
from models.etter import Function, FunctionWorkflow, WorkflowTask, MasterCompany, MasterFunction, WorkflowBuilderSampleData
from models.auth import User
from common.db_utils import get_or_create_master_function, upsert_master_function, generic_upsert
from services.etter import bulk_upsert_workflow_builder_sample_data, delete_workflow_builder_sample_data
from common.logger import logger
from schemas.etter_schemas import (
    FunctionCreate,
    FunctionUpdate,
    WorkflowCreate,
    WorkflowUpdate,
    TaskCreate,
    TaskUpdate,
    ComprehensiveFunctionWorkflowCreate,
    TaskSourceRequest,
    TaskSourceResponse,
    MasterFunctionBulkUpsertRequest,
    MasterFunctionDeleteRequest,
    SubFunctionScoreRequest,
    SubFunctionScoreResponse,
    SubFunctionScoreItem,
    EnsureFunctionRequest,
    EnsureFunctionResponse,
    WorkflowBuilderSampleDataBulkUpsertRequest,
    WorkflowBuilderSampleDataBulkUpsertResponse,
    WorkflowBuilderSampleDataDeleteRequest,
    WorkflowBuilderSampleDataDeleteResponse,
    WorkflowBuilderSampleDataResponse,
)
from pydantic import BaseModel

function_workflow_task_router = APIRouter(prefix="/etter", tags=["Function-Workflow-Task"])


@function_workflow_task_router.post("/bulk-upsert-master-functions", status_code=status.HTTP_201_CREATED)
def bulk_upsert_master_functions(
    request_data: MasterFunctionBulkUpsertRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        created_functions = []
        updated_functions = []
        errors = []

        for idx, item in enumerate(request_data.data):
            try:
                db.flush()

                master_function, created = get_or_create_master_function(
                    db=db,
                    high_level_func=item.high_level_func,
                    sub_level_func=item.sub_level_func
                )

                if not created:
                    master_function.updated_by = datetime.utcnow()
                    db.flush()
                    updated_functions.append({
                        "id": master_function.id,
                        "high_level_func": master_function.high_level_func,
                        "sub_level_func": master_function.sub_level_func,
                        "updated_by": master_function.updated_by
                    })
                else:
                    created_functions.append({
                        "id": master_function.id,
                        "high_level_func": master_function.high_level_func,
                        "sub_level_func": master_function.sub_level_func,
                        "updated_by": master_function.updated_by
                    })

            except IntegrityError as ie:
                errors.append({
                    "index": idx,
                    "high_level_func": item.high_level_func,
                    "sub_level_func": item.sub_level_func,
                    "error": f"Duplicate function or integrity constraint violation: {str(ie.orig)}"
                })
            except Exception as e:
                errors.append({
                    "index": idx,
                    "high_level_func": item.high_level_func,
                    "sub_level_func": item.sub_level_func,
                    "error": str(e)
                })

        db.commit()

        return {
            "status": "success",
            "data": {
                "created": created_functions,
                "updated": updated_functions,
                "errors": errors,
                "total_created": len(created_functions),
                "total_updated": len(updated_functions),
                "total_errors": len(errors)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.delete("/delete-master-function", status_code=status.HTTP_200_OK)
def delete_master_function(
    request_data: MasterFunctionDeleteRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    master_function = db.query(MasterFunction).filter(
        MasterFunction.high_level_func == request_data.high_level_func,
        MasterFunction.sub_level_func == request_data.sub_level_func
    ).first()

    if not master_function:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MasterFunction not found"
        )

    functions = db.query(Function).filter(
        Function.master_function_id == master_function.id
    ).all()

    for function in functions:
        workflows = db.query(FunctionWorkflow).filter(
            FunctionWorkflow.function_id == function.id
        ).all()

        for workflow in workflows:
            db.execute(delete(WorkflowTask).where(WorkflowTask.workflow_id == workflow.id))
            db.delete(workflow)

        db.delete(function)

    db.delete(master_function)
    db.commit()

    return {
        "status": "success",
        "message": "MasterFunction and all associated Functions, Workflows, and Tasks deleted successfully"
    }


def normalize_automation_priority(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    return value.capitalize() if value else None


@function_workflow_task_router.post("/create-function", status_code=status.HTTP_201_CREATED)
def create_function(
    function_data: FunctionCreate,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        master_function, _ = get_or_create_master_function(
            db=db,
            high_level_func=function_data.high_level_func,
            sub_level_func=function_data.sub_level_func
        )

        existing_function = db.query(Function).filter(
            Function.master_function_id == master_function.id,
            Function.company_id == function_data.company_id
        ).first()

        if existing_function:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Function with this master_function already exists for this company"
            )

        new_function, _ = generic_upsert(
            db=db,
            model_class=Function,
            unique_keys={
                'master_function_id': master_function.id,
                'company_id': function_data.company_id
            },
            update_data={
                'description': function_data.description,
                'score': function_data.score
            },
            commit=True
        )
        db.refresh(new_function)

        return {
            "status": "success",
            "data": {
                "id": new_function.id,
                "master_function_id": new_function.master_function_id,
                "high_level_func": master_function.high_level_func,
                "sub_level_func": master_function.sub_level_func,
                "description": new_function.description,
                "score": new_function.score,
                "company_id": new_function.company_id,
                "created_on": new_function.created_on
            }
        }
    except HTTPException:
        raise
    except DataError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data validation error: {str(e.orig)}"
        )
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database constraint violation: {str(e.orig)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.get("/get-function/{function_id}", status_code=status.HTTP_200_OK)
def get_function(
    function_id: int,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    function = db.query(Function).filter(Function.id == function_id).first()
    if not function:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Function not found"
        )

    master_function = db.query(MasterFunction).filter(
        MasterFunction.id == function.master_function_id
    ).first()

    return {
        "status": "success",
        "data": {
            "id": function.id,
            "master_function_id": function.master_function_id,
            "high_level_func": master_function.high_level_func if master_function else None,
            "sub_level_func": master_function.sub_level_func if master_function else None,
            "description": function.description,
            "score": function.score,
            "company_id": function.company_id,
            "created_on": function.created_on,
            "modified_on": function.modified_on
        }
    }


@function_workflow_task_router.get("/get-functions", status_code=status.HTTP_200_OK)
def get_all_functions(
    company_id: Optional[int] = None,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    query = db.query(Function)
    if company_id:
        query = query.filter(Function.company_id == company_id)

    functions = query.all()

    result = []
    for func in functions:
        master_function = db.query(MasterFunction).filter(
            MasterFunction.id == func.master_function_id
        ).first()
        result.append({
            "id": func.id,
            "master_function_id": func.master_function_id,
            "high_level_func": master_function.high_level_func if master_function else None,
            "sub_level_func": master_function.sub_level_func if master_function else None,
            "description": func.description,
            "score": func.score,
            "company_id": func.company_id,
            "created_on": func.created_on,
            "modified_on": func.modified_on
        })

    return {
        "status": "success",
        "data": result
    }


@function_workflow_task_router.put("/update-function/{function_id}", status_code=status.HTTP_200_OK)
def update_function(
    function_id: int,
    function_data: FunctionUpdate,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        function = db.query(Function).filter(Function.id == function_id).first()
        if not function:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Function not found"
            )

        if function_data.high_level_func is not None and function_data.sub_level_func is not None:
            master_function, _ = get_or_create_master_function(
                db=db,
                high_level_func=function_data.high_level_func,
                sub_level_func=function_data.sub_level_func
            )

            new_company_id = function_data.company_id if function_data.company_id is not None else function.company_id
            existing_function = db.query(Function).filter(
                Function.master_function_id == master_function.id,
                Function.company_id == new_company_id,
                Function.id != function_id
            ).first()

            if existing_function:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Function with this master_function already exists for this company"
                )

            function.master_function_id = master_function.id

        if function_data.description is not None:
            function.description = function_data.description
        if function_data.score is not None:
            function.score = function_data.score
        if function_data.company_id is not None:
            function.company_id = function_data.company_id

        function.modified_on = datetime.utcnow()

        db.commit()
        db.refresh(function)

        master_function = db.query(MasterFunction).filter(
            MasterFunction.id == function.master_function_id
        ).first()

        return {
            "status": "success",
            "data": {
                "id": function.id,
                "master_function_id": function.master_function_id,
                "high_level_func": master_function.high_level_func if master_function else None,
                "sub_level_func": master_function.sub_level_func if master_function else None,
                "description": function.description,
                "score": function.score,
                "company_id": function.company_id,
                "created_on": function.created_on,
                "modified_on": function.modified_on
            }
        }
    except HTTPException:
        raise
    except DataError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data validation error: {str(e.orig)}"
        )
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database constraint violation: {str(e.orig)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.delete("/delete-function/{function_id}", status_code=status.HTTP_200_OK)
def delete_function(
    function_id: int,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    function = db.query(Function).filter(Function.id == function_id).first()
    if not function:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Function not found"
        )

    workflows = db.query(FunctionWorkflow).filter(FunctionWorkflow.function_id == function_id).all()
    if workflows:
        workflow_ids = [workflow.id for workflow in workflows]
        db.execute(delete(WorkflowTask).where(WorkflowTask.workflow_id.in_(workflow_ids)))
        db.execute(delete(FunctionWorkflow).where(FunctionWorkflow.id.in_(workflow_ids)))

    db.delete(function)
    db.commit()

    return {
        "status": "success",
        "message": "Function deleted successfully"
    }


@function_workflow_task_router.get("/get-function-workflows", status_code=status.HTTP_200_OK)
def get_workflows_for_function(
    high_level_func: str,
    sub_level_func: str,
    company_id: int,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    master_function = db.query(MasterFunction).filter(
        MasterFunction.high_level_func == high_level_func,
        MasterFunction.sub_level_func == sub_level_func
    ).first()

    if not master_function:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MasterFunction not found"
        )

    function = db.query(Function).filter(
        Function.master_function_id == master_function.id,
        Function.company_id == company_id
    ).first()
    if not function:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Function not found"
        )

    workflows = db.query(FunctionWorkflow).filter(
        FunctionWorkflow.function_id == function.id
    ).all()

    return {
        "status": "success",
        "data": [
            {
                "id": wf.id,
                "workflow_name": wf.workflow_name,
                "description": wf.description,
                "score": wf.score,
                "researcher_id": wf.researcher_id,
                "approver_id": wf.approver_id,
                "approval_status": wf.approval_status,
                "function_id": wf.function_id,
                "created_on": wf.created_on,
                "modified_on": wf.modified_on,
                "insights": wf.insights,
                "priority": wf.priority,
                "frequency": wf.frequency,
                "objective": wf.objective,
                "source": wf.source
            }
            for wf in workflows
        ]
    }


@function_workflow_task_router.post("/create-workflow", status_code=status.HTTP_201_CREATED)
def create_workflow(
    workflow_data: WorkflowCreate,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        function = db.query(Function).filter(Function.id == workflow_data.function_id).first()
        if not function:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Function not found"
            )

        existing_workflow = db.query(FunctionWorkflow).filter(
            FunctionWorkflow.workflow_name == workflow_data.workflow_name,
            FunctionWorkflow.function_id == workflow_data.function_id
        ).first()

        if existing_workflow:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow with this name already exists for this function"
            )

        new_workflow, _ = generic_upsert(
            db=db,
            model_class=FunctionWorkflow,
            unique_keys={
                'workflow_name': workflow_data.workflow_name,
                'function_id': workflow_data.function_id
            },
            update_data={
                'description': workflow_data.description,
                'score': workflow_data.score,
                'researcher_id': current_user.id,
                'approver_id': workflow_data.approver_id,
                'approval_status': workflow_data.approval_status,
                'insights': workflow_data.insights,
                'priority': workflow_data.priority,
                'frequency': workflow_data.frequency,
                'objective': workflow_data.objective,
                'source': workflow_data.source or "User"
            },
            commit=True
        )
        db.refresh(new_workflow)

        return {
            "status": "success",
            "data": {
                "id": new_workflow.id,
                "workflow_name": new_workflow.workflow_name,
                "description": new_workflow.description,
                "score": new_workflow.score,
                "researcher_id": new_workflow.researcher_id,
                "approver_id": new_workflow.approver_id,
                "approval_status": new_workflow.approval_status,
                "function_id": new_workflow.function_id,
                "created_on": new_workflow.created_on,
                "insights": new_workflow.insights,
                "priority": new_workflow.priority,
                "frequency": new_workflow.frequency,
                "objective": new_workflow.objective,
                "source": new_workflow.source
            }
        }
    except HTTPException:
        raise
    except DataError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data validation error: {str(e.orig)}"
        )
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database constraint violation: {str(e.orig)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.get("/get-workflow/{workflow_id}", status_code=status.HTTP_200_OK)
def get_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    workflow = db.query(FunctionWorkflow).filter(FunctionWorkflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )

    return {
        "status": "success",
        "data": {
            "id": workflow.id,
            "workflow_name": workflow.workflow_name,
            "description": workflow.description,
            "score": workflow.score,
            "researcher_id": workflow.researcher_id,
            "approver_id": workflow.approver_id,
            "approval_status": workflow.approval_status,
            "function_id": workflow.function_id,
            "created_on": workflow.created_on,
            "modified_on": workflow.modified_on,
            "insights": workflow.insights,
            "priority": workflow.priority,
            "frequency": workflow.frequency,
            "objective": workflow.objective,
            "source": workflow.source
        }
    }


@function_workflow_task_router.post("/get-workflows", status_code=status.HTTP_200_OK)
def get_workflows(
    high_level_func: str,
    sub_level_func: str,
    company_id: int,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        master_function, _ = get_or_create_master_function(
            db=db,
            high_level_func=high_level_func,
            sub_level_func=sub_level_func
        )

        function, _ = generic_upsert(
            db=db,
            model_class=Function,
            unique_keys={
                'master_function_id': master_function.id,
                'company_id': company_id
            },
            update_data={},
            commit=True
        )
        db.refresh(function)

        workflows = db.query(FunctionWorkflow).filter(
            FunctionWorkflow.function_id == function.id
        ).all()

        return {
            "status": "success",
            "function": {
                "id": function.id,
                "master_function_id": function.master_function_id,
                "high_level_func": master_function.high_level_func,
                "sub_level_func": master_function.sub_level_func
            },
            "data": [
                {
                    "id": wf.id,
                    "workflow_name": wf.workflow_name,
                    "description": wf.description,
                    "score": wf.score,
                    "researcher_id": wf.researcher_id,
                    "approver_id": wf.approver_id,
                    "approval_status": wf.approval_status,
                    "function_id": wf.function_id,
                    "created_on": wf.created_on,
                    "modified_on": wf.modified_on,
                    "insights": wf.insights,
                    "priority": wf.priority,
                    "frequency": wf.frequency,
                    "objective": wf.objective,
                    "source": wf.source
                }
                for wf in workflows
            ]
        }
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database constraint violation: {str(e.orig)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.put("/update-workflow/{workflow_id}", status_code=status.HTTP_200_OK)
def update_workflow(
    workflow_id: int,
    workflow_data: WorkflowUpdate,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        workflow = db.query(FunctionWorkflow).filter(FunctionWorkflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        if workflow_data.function_id:
            function = db.query(Function).filter(Function.id == workflow_data.function_id).first()
            if not function:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Function not found"
                )

        new_workflow_name = workflow_data.workflow_name if workflow_data.workflow_name is not None else workflow.workflow_name
        new_function_id = workflow_data.function_id if workflow_data.function_id is not None else workflow.function_id

        if new_workflow_name != workflow.workflow_name or new_function_id != workflow.function_id:
            existing_workflow = db.query(FunctionWorkflow).filter(
                FunctionWorkflow.workflow_name == new_workflow_name,
                FunctionWorkflow.function_id == new_function_id,
                FunctionWorkflow.id != workflow_id
            ).first()

            if existing_workflow:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Workflow with this name already exists for this function"
                )

        if workflow_data.workflow_name is not None:
            workflow.workflow_name = workflow_data.workflow_name
        if workflow_data.description is not None:
            workflow.description = workflow_data.description
        if workflow_data.score is not None:
            workflow.score = workflow_data.score
        if workflow_data.approver_id is not None:
            workflow.approver_id = workflow_data.approver_id
        if workflow_data.approval_status is not None:
            workflow.approval_status = workflow_data.approval_status
        if workflow_data.function_id is not None:
            workflow.function_id = workflow_data.function_id
        if workflow_data.insights is not None:
            workflow.insights = workflow_data.insights
        if workflow_data.priority is not None:
            workflow.priority = workflow_data.priority
        if workflow_data.frequency is not None:
            workflow.frequency = workflow_data.frequency
        if workflow_data.objective is not None:
            workflow.objective = workflow_data.objective
        if workflow_data.source is not None:
            workflow.source = workflow_data.source

        workflow.modified_on = datetime.utcnow()

        db.commit()
        db.refresh(workflow)

        return {
            "status": "success",
            "data": {
                "id": workflow.id,
                "workflow_name": workflow.workflow_name,
                "description": workflow.description,
                "score": workflow.score,
                "researcher_id": workflow.researcher_id,
                "approver_id": workflow.approver_id,
                "approval_status": workflow.approval_status,
                "function_id": workflow.function_id,
                "created_on": workflow.created_on,
                "modified_on": workflow.modified_on,
                "insights": workflow.insights,
                "priority": workflow.priority,
                "frequency": workflow.frequency,
                "objective": workflow.objective,
                "source": workflow.source
            }
        }
    except HTTPException:
        raise
    except DataError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data validation error: {str(e.orig)}"
        )
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database constraint violation: {str(e.orig)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.delete("/delete-workflow/{workflow_id}", status_code=status.HTTP_200_OK)
def delete_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    workflow = db.query(FunctionWorkflow).filter(FunctionWorkflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )

    db.execute(delete(WorkflowTask).where(WorkflowTask.workflow_id == workflow_id))
    db.delete(workflow)
    db.commit()

    return {
        "status": "success",
        "message": "Workflow deleted successfully"
    }


@function_workflow_task_router.get("/get-workflow-tasks", status_code=status.HTTP_200_OK)
def get_tasks_for_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    workflow = db.query(FunctionWorkflow).filter(FunctionWorkflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )

    tasks = db.query(WorkflowTask).filter(
        WorkflowTask.workflow_id == workflow_id
    ).order_by(WorkflowTask.position).all()

    return {
        "status": "success",
        "data": [
            {
                "id": task.id,
                "task_name": task.task_name,
                "description": task.description,
                "impact_score": task.impact_score,
                "roles": task.roles,
                "skills_required": task.skills_required,
                "task_type": task.task_type,
                "position": task.position,
                "sequence_number": task.sequence_number,
                "dependencies": task.dependencies,
                "workflow_id": task.workflow_id,
                "created_on": task.created_on,
                "modified_on": task.modified_on,
                "automation_priority": task.automation_priority,
                "score_breakdown": task.score_breakdown
            }
            for task in tasks
        ]
    }


@function_workflow_task_router.post("/create-task", status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        workflow = db.query(FunctionWorkflow).filter(FunctionWorkflow.id == task_data.workflow_id).first()
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        existing_task = db.query(WorkflowTask).filter(
            WorkflowTask.task_name == task_data.task_name,
            WorkflowTask.workflow_id == task_data.workflow_id
        ).first()

        if existing_task:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task with this name already exists for this workflow"
            )

        new_task, _ = generic_upsert(
            db=db,
            model_class=WorkflowTask,
            unique_keys={
                'task_name': task_data.task_name,
                'workflow_id': task_data.workflow_id
            },
            update_data={
                'description': task_data.description,
                'impact_score': task_data.impact_score,
                'roles': task_data.roles,
                'skills_required': task_data.skills_required,
                'task_type': task_data.task_type,
                'position': task_data.position,
                'sequence_number': task_data.sequence_number,
                'dependencies': task_data.dependencies,
                'automation_priority': normalize_automation_priority(task_data.automation_priority),
                'score_breakdown': task_data.score_breakdown
            },
            commit=True
        )
        db.refresh(new_task)

        return {
            "status": "success",
            "data": {
                "id": new_task.id,
                "task_name": new_task.task_name,
                "description": new_task.description,
                "impact_score": new_task.impact_score,
                "roles": new_task.roles,
                "skills_required": new_task.skills_required,
                "task_type": new_task.task_type,
                "position": new_task.position,
                "sequence_number": new_task.sequence_number,
                "dependencies": new_task.dependencies,
                "workflow_id": new_task.workflow_id,
                "created_on": new_task.created_on,
                "automation_priority": new_task.automation_priority,
                "score_breakdown": new_task.score_breakdown
            }
        }
    except HTTPException:
        raise
    except DataError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data validation error: {str(e.orig)}"
        )
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database constraint violation: {str(e.orig)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.get("/get-task/{task_id}", status_code=status.HTTP_200_OK)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    task = db.query(WorkflowTask).filter(WorkflowTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return {
        "status": "success",
        "data": {
            "id": task.id,
            "task_name": task.task_name,
            "description": task.description,
            "impact_score": task.impact_score,
            "roles": task.roles,
            "skills_required": task.skills_required,
            "task_type": task.task_type,
            "position": task.position,
            "workflow_id": task.workflow_id,
            "created_on": task.created_on,
            "modified_on": task.modified_on,
            "automation_priority": task.automation_priority,
            "score_breakdown": task.score_breakdown
        }
    }


@function_workflow_task_router.get("/get-tasks", status_code=status.HTTP_200_OK)
def get_all_tasks(
    workflow_id: Optional[int] = None,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    query = db.query(WorkflowTask)
    if workflow_id:
        query = query.filter(WorkflowTask.workflow_id == workflow_id)

    tasks = query.order_by(WorkflowTask.position).all()

    return {
        "status": "success",
        "data": [
            {
                "id": task.id,
                "task_name": task.task_name,
                "description": task.description,
                "impact_score": task.impact_score,
                "roles": task.roles,
                "skills_required": task.skills_required,
                "task_type": task.task_type,
                "position": task.position,
                "sequence_number": task.sequence_number,
                "dependencies": task.dependencies,
                "workflow_id": task.workflow_id,
                "created_on": task.created_on,
                "modified_on": task.modified_on,
                "automation_priority": task.automation_priority,
                "score_breakdown": task.score_breakdown
            }
            for task in tasks
        ]
    }


@function_workflow_task_router.put("/update-task/{task_id}", status_code=status.HTTP_200_OK)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        task = db.query(WorkflowTask).filter(WorkflowTask.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        update_fields = task_data.model_dump(exclude_unset=True)

        if "workflow_id" in update_fields and update_fields["workflow_id"] is not None:
            workflow = db.query(FunctionWorkflow).filter(FunctionWorkflow.id == update_fields["workflow_id"]).first()
            if not workflow:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workflow not found"
                )

        new_task_name = update_fields.get("task_name", task.task_name)
        new_workflow_id = task.workflow_id if update_fields.get("workflow_id") is None else update_fields["workflow_id"]

        if new_task_name != task.task_name or new_workflow_id != task.workflow_id:
            existing_task = db.query(WorkflowTask).filter(
                WorkflowTask.task_name == new_task_name,
                WorkflowTask.workflow_id == new_workflow_id,
                WorkflowTask.id != task_id
            ).first()

            if existing_task:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Task with this name already exists for this workflow"
                )

        if "task_name" in update_fields:
            task.task_name = update_fields["task_name"]
        if "description" in update_fields:
            task.description = update_fields["description"]
        if "impact_score" in update_fields:
            task.impact_score = update_fields["impact_score"]
        if "roles" in update_fields:
            task.roles = update_fields["roles"]
        if "skills_required" in update_fields:
            task.skills_required = update_fields["skills_required"]
        if "task_type" in update_fields:
            task.task_type = update_fields["task_type"]
        if "position" in update_fields and update_fields["position"] is not None:
            task.position = update_fields["position"]
        if "sequence_number" in update_fields:
            task.sequence_number = update_fields["sequence_number"]
        if "dependencies" in update_fields:
            task.dependencies = update_fields["dependencies"]
        if "workflow_id" in update_fields and update_fields["workflow_id"] is not None:
            task.workflow_id = update_fields["workflow_id"]
        if "automation_priority" in update_fields:
            task.automation_priority = normalize_automation_priority(update_fields["automation_priority"])
        if "score_breakdown" in update_fields:
            task.score_breakdown = update_fields["score_breakdown"]

        task.modified_on = datetime.utcnow()

        db.commit()
        db.refresh(task)

        return {
            "status": "success",
            "data": {
                "id": task.id,
                "task_name": task.task_name,
                "description": task.description,
                "impact_score": task.impact_score,
                "roles": task.roles,
                "skills_required": task.skills_required,
                "task_type": task.task_type,
                "position": task.position,
                "sequence_number": task.sequence_number,
                "dependencies": task.dependencies,
                "workflow_id": task.workflow_id,
                "created_on": task.created_on,
                "modified_on": task.modified_on,
                "automation_priority": task.automation_priority,
                "score_breakdown": task.score_breakdown
            }
        }
    except HTTPException:
        raise
    except DataError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data validation error: {str(e.orig)}"
        )
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database constraint violation: {str(e.orig)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.delete("/delete-task/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    draup_user_data = draup_user.data
    current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    task = db.query(WorkflowTask).filter(WorkflowTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    db.delete(task)
    db.commit()

    return {
        "status": "success",
        "message": "Task deleted successfully"
    }


@function_workflow_task_router.post("/create-comprehensive-workflow", status_code=status.HTTP_201_CREATED)
def create_comprehensive_workflow(
    data: ComprehensiveFunctionWorkflowCreate,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        company = db.query(MasterCompany).filter(MasterCompany.company_name == data.company_name).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company '{data.company_name}' not found"
            )

        functions_data = []
        function_errors = []

        for function_area_data in data.function_areas:
            try:
                master_function, _ = get_or_create_master_function(
                    db=db,
                    high_level_func=function_area_data.high_level_func,
                    sub_level_func=function_area_data.sub_level_func
                )

                function, created = generic_upsert(
                    db=db,
                    model_class=Function,
                    unique_keys={
                        'master_function_id': master_function.id,
                        'company_id': company.id
                    },
                    update_data={},
                    commit=False
                )
                function_status = "created" if created else "exists"

                created_workflows = []
                updated_workflows = []
                workflow_errors = []

                for workflow_data in function_area_data.workflows:
                    try:
                        db.flush()
                        
                        workflow, created = generic_upsert(
                            db=db,
                            model_class=FunctionWorkflow,
                            unique_keys={
                                'workflow_name': workflow_data.workflow_name,
                                'function_id': function.id
                            },
                            update_data={
                                'description': workflow_data.description,
                                'score': workflow_data.ai_optimization_score * 100 if workflow_data.ai_optimization_score else None,
                                'insights': workflow_data.insights,
                                'priority': workflow_data.priority,
                                'frequency': workflow_data.frequency,
                                'objective': workflow_data.objective,
                                'source': workflow_data.source or "User"
                            },
                            commit=False
                        )
                        workflow_is_new = created
                        
                        workflow_result = {
                            "id": workflow.id,
                            "workflow_name": workflow.workflow_name,
                            "description": workflow.description,
                            "score": workflow.score,
                            "insights": workflow.insights,
                            "priority": workflow.priority,
                            "frequency": workflow.frequency,
                            "objective": workflow.objective,
                            "source": workflow.source,
                            "tasks": []
                        }

                        sorted_tasks = sorted(
                            workflow_data.tasks,
                            key=lambda task: task.impact_score if task.impact_score is not None else float("-inf"),
                            reverse=True
                        )

                        for task_index, task_data in enumerate(sorted_tasks):
                            try:
                                db.flush()
                                task_payload = task_data.model_dump(exclude_unset=True)

                                task, created = generic_upsert(
                                    db=db,
                                    model_class=WorkflowTask,
                                    unique_keys={
                                        'task_name': task_data.task_name,
                                        'workflow_id': workflow.id
                                    },
                                    update_data={
                                        'description': task_data.description,
                                        'impact_score': task_data.impact_score,
                                        'roles': task_data.roles,
                                        'task_type': task_data.task_type,
                                        'skills_required': task_data.skills_required,
                                        'automation_priority': normalize_automation_priority(task_data.automation_priority),
                                        'score_breakdown': task_data.score_breakdown,
                                        'position': task_index,
                                        'sequence_number': task_payload.get("sequence_number"),
                                        'dependencies': task_payload.get("dependencies")
                                    },
                                    commit=False
                                )
                                
                                workflow_result["tasks"].append({
                                    "id": task.id,
                                    "task_name": task.task_name,
                                    "description": task.description,
                                    "impact_score": task.impact_score,
                                    "roles": task.roles,
                                    "skills_required": task.skills_required,
                                    "task_type": task.task_type,
                                    "position": task.position,
                                    "sequence_number": task.sequence_number,
                                    "dependencies": task.dependencies,
                                    "automation_priority": task.automation_priority,
                                    "score_breakdown": task.score_breakdown,
                                    "status": "created" if created else "updated"
                                })
                            except Exception as e:
                                workflow_result["tasks"].append({
                                    "task_name": task_data.task_name,
                                    "error": str(e),
                                    "status": "failed"
                                })

                        if workflow_is_new:
                            created_workflows.append(workflow_result)
                        else:
                            updated_workflows.append(workflow_result)

                    except Exception as e:
                        workflow_errors.append({
                            "workflow_name": workflow_data.workflow_name,
                            "error": str(e)
                        })

                functions_data.append({
                    "function": {
                        "id": function.id,
                        "master_function_id": function.master_function_id,
                        "high_level_func": master_function.high_level_func,
                        "sub_level_func": master_function.sub_level_func,
                        "company_name": company.company_name,
                        "status": function_status
                    },
                    "created_workflows": created_workflows,
                    "updated_workflows": updated_workflows,
                    "workflow_errors": workflow_errors,
                    "summary": {
                        "total_workflows_created": len(created_workflows),
                        "total_workflows_updated": len(updated_workflows),
                        "total_workflow_errors": len(workflow_errors),
                        "total_tasks": sum(len(w["tasks"]) for w in created_workflows + updated_workflows)
                    }
                })

            except Exception as e:
                function_errors.append({
                    "high_level_func": function_area_data.high_level_func,
                    "sub_level_func": function_area_data.sub_level_func,
                    "error": str(e)
                })

        db.commit()

        total_created_workflows = sum(len(f["created_workflows"]) for f in functions_data)
        total_updated_workflows = sum(len(f["updated_workflows"]) for f in functions_data)
        total_workflow_errors = sum(len(f["workflow_errors"]) for f in functions_data)
        total_tasks = sum(f["summary"]["total_tasks"] for f in functions_data)

        return {
            "status": "success",
            "data": {
                "functions": functions_data,
                "function_errors": function_errors,
                "summary": {
                    "total_functions_processed": len(functions_data),
                    "total_functions_failed": len(function_errors),
                    "total_workflows_created": total_created_workflows,
                    "total_workflows_updated": total_updated_workflows,
                    "total_workflow_errors": total_workflow_errors,
                    "total_tasks": total_tasks
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


class CreateWorkflowFromSampleRequest(BaseModel):
    company_name: str
    high_level_func: str


@function_workflow_task_router.post("/create-workflow-from-sample", status_code=status.HTTP_201_CREATED)
def create_workflow_from_sample(
    request: CreateWorkflowFromSampleRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        company = db.query(MasterCompany).filter(MasterCompany.company_name == request.company_name).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company '{request.company_name}' not found"
            )

        master_functions = db.query(MasterFunction).filter(
            MasterFunction.high_level_func == request.high_level_func
        ).all()

        if not master_functions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No MasterFunction found with high_level_func '{request.high_level_func}'"
            )

        master_function_ids = [mf.id for mf in master_functions]

        company_sample_data_records = db.query(WorkflowBuilderSampleData).filter(
            WorkflowBuilderSampleData.company_id == company.id,
            WorkflowBuilderSampleData.master_function_id.in_(master_function_ids)
        ).all()

        company_sample_data_map = {record.master_function_id: record for record in company_sample_data_records}

        sample_data_records = []
        for master_function_id in master_function_ids:
            if master_function_id in company_sample_data_map:
                sample_data_records.append(company_sample_data_map[master_function_id])
            else:
                global_record = db.query(WorkflowBuilderSampleData).filter(
                    WorkflowBuilderSampleData.master_function_id == master_function_id,
                    WorkflowBuilderSampleData.is_global == True
                ).first()
                if global_record:
                    sample_data_records.append(global_record)

        if not sample_data_records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No WorkflowBuilderSampleData found for company '{request.company_name}' and high_level_func '{request.high_level_func}', and no global data found for the function"
            )

        success_count = 0
        failure_count = 0
        errors = []

        for record in sample_data_records:
            try:
                sample_data = record.data
                if not isinstance(sample_data, dict):
                    raise ValueError("Sample data must be a dictionary")

                sample_data["company_name"] = request.company_name

                comprehensive_payload = ComprehensiveFunctionWorkflowCreate.model_validate(sample_data)
                create_comprehensive_workflow(comprehensive_payload, db, draup_user)
                success_count += 1
            except ValidationError as e:
                failure_count += 1
                errors.append(f"Record ID {record.id}: Invalid data structure - {str(e)}")
            except HTTPException as e:
                failure_count += 1
                errors.append(f"Record ID {record.id}: {e.detail}")
            except Exception as e:
                failure_count += 1
                errors.append(f"Record ID {record.id}: {str(e)}")

        if failure_count > 0 and success_count == 0:
            return {
                "status": "failure",
                "message": f"All {failure_count} records failed to process"
            }
        elif failure_count > 0:
            return {
                "status": "partial_success",
                "message": f"Processed {success_count} successfully, {failure_count} failed"
            }
        else:
            return {
                "status": "success",
                "message": f"Successfully processed {success_count} record(s)"
            }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.post("/bulk-upsert-functions", status_code=status.HTTP_201_CREATED)
def bulk_upsert_functions(
    functions_data: List[FunctionCreate],
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        created_functions = []
        updated_functions = []
        errors = []

        for idx, function_data in enumerate(functions_data):
            try:
                db.flush()
                
                master_function, _ = get_or_create_master_function(
                    db=db,
                    high_level_func=function_data.high_level_func,
                    sub_level_func=function_data.sub_level_func
                )
                
                function, created = generic_upsert(
                    db=db,
                    model_class=Function,
                    unique_keys={
                        'master_function_id': master_function.id,
                        'company_id': function_data.company_id
                    },
                    update_data={
                        'description': function_data.description,
                        'score': function_data.score
                    },
                    commit=False
                )
                
                function_dict = {
                    "id": function.id,
                    "master_function_id": function.master_function_id,
                    "high_level_func": master_function.high_level_func,
                    "sub_level_func": master_function.sub_level_func,
                    "description": function.description,
                    "score": function.score,
                    "company_id": function.company_id,
                    "created_on": function.created_on,
                    "modified_on": function.modified_on
                }
                
                if created:
                    created_functions.append(function_dict)
                else:
                    updated_functions.append(function_dict)

            except IntegrityError as ie:
                errors.append({
                    "index": idx,
                    "high_level_func": function_data.high_level_func,
                    "sub_level_func": function_data.sub_level_func,
                    "error": f"Duplicate function or integrity constraint violation: {str(ie.orig)}"
                })
            except Exception as e:
                errors.append({
                    "index": idx,
                    "high_level_func": function_data.high_level_func,
                    "sub_level_func": function_data.sub_level_func,
                    "error": str(e)
                })

        db.commit()

        return {
            "status": "success",
            "data": {
                "created": created_functions,
                "updated": updated_functions,
                "errors": errors,
                "total_created": len(created_functions),
                "total_updated": len(updated_functions),
                "total_errors": len(errors)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.post("/bulk-upsert-workflows", status_code=status.HTTP_201_CREATED)
def bulk_upsert_workflows(
    workflows_data: List[WorkflowCreate],
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        created_workflows = []
        updated_workflows = []
        errors = []

        for idx, workflow_data in enumerate(workflows_data):
            try:
                db.flush()
                
                function = db.query(Function).filter(Function.id == workflow_data.function_id).first()
                if not function:
                    errors.append({
                        "index": idx,
                        "workflow_name": workflow_data.workflow_name,
                        "error": "Function not found"
                    })
                    continue

                workflow, created = generic_upsert(
                    db=db,
                    model_class=FunctionWorkflow,
                    unique_keys={
                        'workflow_name': workflow_data.workflow_name,
                        'function_id': workflow_data.function_id
                    },
                    update_data={
                        'description': workflow_data.description,
                        'score': workflow_data.score,
                        'researcher_id': current_user.id,
                        'approver_id': workflow_data.approver_id,
                        'approval_status': workflow_data.approval_status,
                        'insights': workflow_data.insights,
                        'priority': workflow_data.priority,
                        'frequency': workflow_data.frequency,
                        'objective': workflow_data.objective,
                        'source': workflow_data.source or "User"
                    },
                    commit=False
                )
                
                workflow_dict = {
                    "id": workflow.id,
                    "workflow_name": workflow.workflow_name,
                    "description": workflow.description,
                    "score": workflow.score,
                    "researcher_id": workflow.researcher_id,
                    "approver_id": workflow.approver_id,
                    "approval_status": workflow.approval_status,
                    "function_id": workflow.function_id,
                    "created_on": workflow.created_on,
                    "modified_on": workflow.modified_on,
                    "insights": workflow.insights,
                    "priority": workflow.priority,
                    "frequency": workflow.frequency,
                    "objective": workflow.objective,
                    "source": workflow.source
                }
                
                if created:
                    created_workflows.append(workflow_dict)
                else:
                    updated_workflows.append(workflow_dict)

            except IntegrityError as ie:
                errors.append({
                    "index": idx,
                    "workflow_name": workflow_data.workflow_name,
                    "error": f"Duplicate workflow or integrity constraint violation: {str(ie.orig)}"
                })
            except Exception as e:
                errors.append({
                    "index": idx,
                    "workflow_name": workflow_data.workflow_name,
                    "error": str(e)
                })

        db.commit()

        return {
            "status": "success",
            "data": {
                "created": created_workflows,
                "updated": updated_workflows,
                "errors": errors,
                "total_created": len(created_workflows),
                "total_updated": len(updated_workflows),
                "total_errors": len(errors)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.post("/bulk-upsert-tasks", status_code=status.HTTP_201_CREATED)
def bulk_upsert_tasks(
    tasks_data: List[TaskCreate],
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        created_tasks = []
        updated_tasks = []
        errors = []

        for idx, task_data in enumerate(tasks_data):
            try:
                db.flush()
                task_payload = task_data.model_dump(exclude_unset=True)

                workflow = db.query(FunctionWorkflow).filter(FunctionWorkflow.id == task_data.workflow_id).first()
                if not workflow:
                    errors.append({
                        "index": idx,
                        "task_name": task_data.task_name,
                        "error": "Workflow not found"
                    })
                    continue

                task, created = generic_upsert(
                    db=db,
                    model_class=WorkflowTask,
                    unique_keys={
                        'task_name': task_data.task_name,
                        'workflow_id': task_data.workflow_id
                    },
                    update_data={
                        'description': task_data.description,
                        'impact_score': task_data.impact_score,
                        'roles': task_data.roles,
                        'skills_required': task_data.skills_required,
                        'task_type': task_data.task_type,
                        'position': task_data.position,
                        'sequence_number': task_payload.get("sequence_number"),
                        'dependencies': task_payload.get("dependencies"),
                        'automation_priority': normalize_automation_priority(task_data.automation_priority),
                        'score_breakdown': task_data.score_breakdown
                    },
                    commit=False
                )
                
                task_dict = {
                    "id": task.id,
                    "task_name": task.task_name,
                    "description": task.description,
                    "impact_score": task.impact_score,
                    "roles": task.roles,
                    "skills_required": task.skills_required,
                    "task_type": task.task_type,
                    "position": task.position,
                    "sequence_number": task.sequence_number,
                    "dependencies": task.dependencies,
                    "workflow_id": task.workflow_id,
                    "created_on": task.created_on,
                    "modified_on": task.modified_on,
                    "automation_priority": task.automation_priority,
                    "score_breakdown": task.score_breakdown
                }
                
                if created:
                    created_tasks.append(task_dict)
                else:
                    updated_tasks.append(task_dict)

            except IntegrityError as ie:
                errors.append({
                    "index": idx,
                    "task_name": task_data.task_name,
                    "error": f"Duplicate task or integrity constraint violation: {str(ie.orig)}"
                })
            except Exception as e:
                errors.append({
                    "index": idx,
                    "task_name": task_data.task_name,
                    "error": str(e)
                })

        db.commit()

        return {
            "status": "success",
            "data": {
                "created": created_tasks,
                "updated": updated_tasks,
                "errors": errors,
                "total_created": len(created_tasks),
                "total_updated": len(updated_tasks),
                "total_errors": len(errors)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.post("/get-tasks-source", status_code=status.HTTP_200_OK)
def get_tasks_source(
    request_data: TaskSourceRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    """
    Get tasks from multiple sources based on provided parameters.
    
    Priority logic:
    1. If role and company provided -> Fetch from Neo4j via role assessment API
    2. Else if workflow_id or workflow_name provided -> Fetch from Postgres WorkflowTask table
    3. Else if only company provided -> Fetch from task consolidator API
    4. Otherwise -> Return error
    
    Args:
        request_data: TaskSourceRequest with optional company, role, workflow_id, workflow_name, function_id
        db: Database session
        draup_user: Authenticated user
        
    Returns:
        TaskSourceResponse with source, tasks list, and metadata
        
    Note:
        - workflow_name requires function_id (workflow names are only unique within a function)
        - workflow_id takes precedence over workflow_name if both are provided
        - If workflow_name is used without workflow_id, function_id is required
    """
    from services.etter import get_tasks_from_sources
    
    try:
        # Validate user authentication
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Extract parameters
        company = request_data.company
        role = request_data.role
        workflow_id = request_data.workflow_id
        workflow_name = request_data.workflow_name
        function_id = request_data.function_id
        
        # Call service function to get tasks from appropriate source
        result = get_tasks_from_sources(
            company=company,
            role=role,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            function_id=function_id,
            db=db
        )
        
        # Check for errors in result
        if "error" in result:
            error_code = result.get("error_code", "UNKNOWN_ERROR")
            
            if error_code == "INVALID_PARAMETERS":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"]
                )
            elif error_code in ["ROLE_NOT_FOUND", "WORKFLOW_NOT_FOUND"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["error"]
                )
            elif error_code in ["AUTH_FAILED", "API_ERROR", "TIMEOUT", "DATABASE_ERROR", "INTERNAL_ERROR"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )
        
        # Build response (tasks are already a list of strings)
        response = TaskSourceResponse(
            status="success",
            source=result["source"],
            tasks=result["tasks"],
            metadata=result["metadata"]
        )
        
        return response
        
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.post("/get-sub-functions-with-scores", status_code=status.HTTP_200_OK)
def get_sub_functions_with_scores(
    request_data: SubFunctionScoreRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    """
    Get all sub-functions for a given high-level function and company with their average workflow scores.
    
    Args:
        request_data: SubFunctionScoreRequest with high_level_func and company_id
        db: Database session
        draup_user: Authenticated user
        
    Returns:
        SubFunctionScoreResponse with list of sub-functions including:
        - function details (id, master_function_id, sub_level_func, description)
        - function_score (score stored on the function itself)
        - average_workflow_score (average of all workflow scores for that function)
        - workflow_count (number of workflows under that function)
    """
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        company = db.query(MasterCompany).filter(MasterCompany.id == request_data.company_id).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID {request_data.company_id} not found"
            )
        
        master_functions = db.query(MasterFunction).filter(
            MasterFunction.high_level_func == request_data.high_level_func
        ).all()
        
        if not master_functions:
            return SubFunctionScoreResponse(
                status="success",
                high_level_func=request_data.high_level_func,
                company_id=request_data.company_id,
                company_name=company.company_name,
                sub_functions=[],
                total_count=0
            )
        
        master_function_ids = [mf.id for mf in master_functions]
        master_func_map = {mf.id: mf for mf in master_functions}
        
        functions = db.query(Function).filter(
            Function.master_function_id.in_(master_function_ids),
            Function.company_id == request_data.company_id
        ).all()
        
        if not functions:
            return SubFunctionScoreResponse(
                status="success",
                high_level_func=request_data.high_level_func,
                company_id=request_data.company_id,
                company_name=company.company_name,
                sub_functions=[],
                total_count=0
            )
        
        function_ids = [f.id for f in functions]
        
        workflow_stats = db.query(
            FunctionWorkflow.function_id,
            func.avg(FunctionWorkflow.score).label('avg_score'),
            func.count(FunctionWorkflow.id).label('workflow_count')
        ).filter(
            FunctionWorkflow.function_id.in_(function_ids)
        ).group_by(FunctionWorkflow.function_id).all()
        
        workflow_stats_map = {
            stat.function_id: {
                'avg_score': float(stat.avg_score) if stat.avg_score is not None else None,
                'workflow_count': stat.workflow_count
            }
            for stat in workflow_stats
        }
        
        sub_functions = []
        for function in functions:
            master_func = master_func_map.get(function.master_function_id)
            stats = workflow_stats_map.get(function.id, {'avg_score': None, 'workflow_count': 0})
            
            sub_functions.append(SubFunctionScoreItem(
                function_id=function.id,
                master_function_id=function.master_function_id,
                sub_level_func=master_func.sub_level_func if master_func else "",
                description=function.description,
                function_score=function.score,
                average_workflow_score=stats['avg_score'],
                workflow_count=stats['workflow_count'],
                created_on=function.created_on,
                modified_on=function.modified_on
            ))
        
        sub_functions.sort(key=lambda x: x.sub_level_func)
        
        return SubFunctionScoreResponse(
            status="success",
            high_level_func=request_data.high_level_func,
            company_id=request_data.company_id,
            company_name=company.company_name,
            sub_functions=sub_functions,
            total_count=len(sub_functions)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.post("/ensure-function", status_code=status.HTTP_201_CREATED)
def ensure_function(
    request_data: EnsureFunctionRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token)
):
    """
    Ensure a function entry exists for a company with the given high-level and sub-level function.
    
    Creates master function entry if it doesn't exist, then creates or returns existing function entry.
    
    Args:
        request_data: EnsureFunctionRequest with high_level_func, sub_level_func, company_id
        db: Database session
        draup_user: Authenticated user
        
    Returns:
        EnsureFunctionResponse with:
        - created: boolean indicating if a new function was created
        - function: the function details
        - master_function: the master function details
    """
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        company = db.query(MasterCompany).filter(MasterCompany.id == request_data.company_id).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID {request_data.company_id} not found"
            )
        
        master_function, master_created = get_or_create_master_function(
            db=db,
            high_level_func=request_data.high_level_func,
            sub_level_func=request_data.sub_level_func
        )
        
        update_data = {}
        if request_data.description is not None:
            update_data['description'] = request_data.description
        if request_data.score is not None:
            update_data['score'] = request_data.score
        
        function, function_created = generic_upsert(
            db=db,
            model_class=Function,
            unique_keys={
                'master_function_id': master_function.id,
                'company_id': request_data.company_id
            },
            update_data=update_data,
            commit=True
        )
        db.refresh(function)
        
        return EnsureFunctionResponse(
            status="success",
            created=function_created,
            function={
                "id": function.id,
                "master_function_id": function.master_function_id,
                "description": function.description,
                "score": function.score,
                "company_id": function.company_id,
                "company_name": company.company_name,
                "created_on": function.created_on,
                "modified_on": function.modified_on
            },
            master_function={
                "id": master_function.id,
                "high_level_func": master_function.high_level_func,
                "sub_level_func": master_function.sub_level_func,
                "created": master_created
            }
        )
        
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database constraint violation: {str(e.orig)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@function_workflow_task_router.post("/workflow_builder_sample_data/bulk_upsert")
def bulk_upsert_workflow_builder_sample_data_endpoint(
    request: WorkflowBuilderSampleDataBulkUpsertRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = WorkflowBuilderSampleDataBulkUpsertResponse(status="success", data=None, errors=[])
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        items = [item.model_dump() for item in request.items]
        results = bulk_upsert_workflow_builder_sample_data(
            db=db, 
            items=items, 
            company_name=request.company_name,
            current_user=current_user
        )
        
        resp_obj.data = []
        for item in results:
            master_function = db.query(MasterFunction).filter(MasterFunction.id == item.master_function_id).first()
            resp_obj.data.append(WorkflowBuilderSampleDataResponse(
                id=item.id,
                master_function_id=item.master_function_id,
                high_level_func=master_function.high_level_func if master_function else "",
                sub_level_func=master_function.sub_level_func if master_function else "",
                is_global=item.is_global,
                data=item.data,
                company_id=item.company_id,
                created_by=item.created_by,
                modified_by=item.modified_by,
                created_on=item.created_on,
                modified_on=item.modified_on
            ))
    except HTTPException:
        raise
    except Exception as e:
        resp_obj.status = "failure"
        resp_obj.errors.append(f"Error upserting workflow builder sample data: {str(e)}")
        logger.error(f"Error upserting workflow builder sample data: {str(e)}", exc_info=True)
    
    return resp_obj


@function_workflow_task_router.delete("/workflow_builder_sample_data")
def delete_workflow_builder_sample_data_endpoint(
    request: WorkflowBuilderSampleDataDeleteRequest,
    db: Session = Depends(get_db),
    draup_user: ResponseModel = Depends(verify_token),
):
    resp_obj = WorkflowBuilderSampleDataDeleteResponse(
        status="success",
        message="",
        deleted_count=0,
        errors=[]
    )
    try:
        deleted_count = delete_workflow_builder_sample_data(
            db=db,
            id=request.id,
            company_name=request.company_name,
            high_level_func=request.high_level_func,
            sub_level_func=request.sub_level_func
        )
        resp_obj.deleted_count = deleted_count
        resp_obj.message = f"Successfully deleted {deleted_count} record(s)"
    except HTTPException:
        raise
    except Exception as e:
        resp_obj.status = "failure"
        resp_obj.errors.append(f"Error deleting workflow builder sample data: {str(e)}")
        logger.error(f"Error deleting workflow builder sample data: {str(e)}", exc_info=True)
    
    return resp_obj

