"""
Extraction API Router

Endpoints for managing document extraction sessions, processing documents,
and handling approval workflows.
"""

import json
import logging
import os
from datetime import datetime
from itertools import groupby
from typing import Dict, List, Optional, Union, Type, Callable, Any, Dict as DictType
from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import cast, or_, select, and_, delete
from sqlalchemy.dialects.postgresql import JSONB

from common.common_utils import get_minimized_time_ago
from common.pagination import paginate
from settings.database import get_db
from api.s3.dependencies import get_uow, get_s3_service
from api.s3.infra.db.uow import UnitOfWork
from api.s3.infra.s3.s3_management_service import S3ManagementService
from models.extraction import (
    ExtractionSession, ExtractedDocument, RoleTaxonomy, SkillTaxonomy, TechStackTaxonomy,
    MasterSkillTaxonomyCategories, MasterTechStackCategory, MasterTechStack,
    ExtractionStatus, ApprovalStatus, ExtractionSessionStatus,
    skill_taxonomy_role_association, tech_stack_taxonomy_role_association
)
from schemas.extraction_schemas import *
from models.auth import User
from models.etter import (
    MasterCompany, MasterCompanyRoleManagementLevel, MasterCompanyRoleJobTrack,
    MasterCompanyRoleJobFamily, MasterCompanyRoleOccupation
)
from models.s3 import Document, DocumentStatus
from services.extraction_service import ExtractionService
from services.auth import verify_token, ResponseModel, create_user

logger = logging.getLogger(__name__)

extraction_router = APIRouter(prefix="/extraction", tags=["Extraction"])
security = HTTPBearer()


# ==================== Helper Functions ====================

def get_user_name(user: Optional[User]) -> Optional[str]:
    """Get full name from User object."""
    if user:
        return f"{user.first_name} {user.last_name}".strip()
    return None


def group_records_by_key(
    records: List,
    key_func: callable,
    builder_func: callable
) -> Dict[str, List]:
    """
    Group sorted records by a key function and build response objects.
    
    Args:
        records: List of records sorted by the grouping field
        key_func: Function that extracts the grouping key from a record
        builder_func: Function that builds a response object from a record
    
    Returns:
        Dictionary mapping group keys to lists of response objects
    """
    grouped_data: Dict[str, List] = {}
    for group_key, group_records in groupby(records, key=key_func):
        grouped_data[group_key] = [builder_func(record) for record in group_records]
    return grouped_data


def get_master_table_names(
    db: Session,
    records: List[RoleTaxonomy]
) -> dict:
    """
    Fetch master table names for all FK relationships efficiently.
    
    Returns dict with keys: 'occupation', 'job_family', 'job_track', 'management_level'
    Each contains a dict mapping ID to name.
    """
    master_names = {
        'occupation': {},
        'job_family': {},
        'job_track': {},
        'management_level': {}
    }
    
    occupation_ids = {r.occupation_id for r in records if r.occupation_id}
    job_family_ids = {r.job_family_id for r in records if r.job_family_id}
    job_track_ids = {r.job_track_id for r in records if r.job_track_id}
    management_level_ids = {r.management_level_id for r in records if r.management_level_id}
    
    if occupation_ids:
        occupations = db.query(MasterCompanyRoleOccupation).filter(
            MasterCompanyRoleOccupation.id.in_(occupation_ids)
        ).all()
        master_names['occupation'] = {occ.id: occ.name for occ in occupations}
    
    if job_family_ids:
        job_families = db.query(MasterCompanyRoleJobFamily).filter(
            MasterCompanyRoleJobFamily.id.in_(job_family_ids)
        ).all()
        master_names['job_family'] = {jf.id: jf.name for jf in job_families}
    
    if job_track_ids:
        job_tracks = db.query(MasterCompanyRoleJobTrack).filter(
            MasterCompanyRoleJobTrack.id.in_(job_track_ids)
        ).all()
        master_names['job_track'] = {jt.id: jt.name for jt in job_tracks}
    
    if management_level_ids:
        management_levels = db.query(MasterCompanyRoleManagementLevel).filter(
            MasterCompanyRoleManagementLevel.id.in_(management_level_ids)
        ).all()
        master_names['management_level'] = {ml.id: ml.name for ml in management_levels}
    
    return master_names


def get_skill_master_category_names(
    db: Session,
    records: List[SkillTaxonomy]
) -> dict:
    """
    Fetch master category names for skill taxonomy records efficiently.
    
    Returns dict mapping category_id to category name.
    """
    category_names = {}
    
    category_ids = {record.category_id for record in records if record.category_id}
    
    if category_ids:
        categories = db.query(MasterSkillTaxonomyCategories).filter(
            MasterSkillTaxonomyCategories.id.in_(category_ids)
        ).all()
        category_names = {cat.id: cat.name for cat in categories}
    
    return category_names


def get_tech_stack_master_category_names(
    db: Session,
    records: List[TechStackTaxonomy]
) -> dict:
    """
    Fetch master category names for tech stack taxonomy records efficiently.
    
    Returns dict mapping category_id to category name.
    """
    category_ids = {r.category_id for r in records if r.category_id}
    category_names = {}
    if category_ids:
        categories = db.query(MasterTechStackCategory).filter(
            MasterTechStackCategory.id.in_(category_ids)
        ).all()
        category_names = {cat.id: cat.name for cat in categories}
    return category_names


# ==================== Taxonomy Configuration ====================

@dataclass
class TaxonomyConfig:
    """Configuration for a taxonomy type."""
    model_class: Type
    response_schema_class: Type
    bulk_upsert_item_schema: Type
    bulk_upsert_request_schema: Type
    bulk_upsert_response_schema: Type
    bulk_approve_request_schema: Type
    bulk_approve_response_schema: Type
    delete_response_schema: Type
    list_response_schema: Type
    name_field: str  # Field name for the main name (job_title, skill_name, tech_stack_name)
    name_filter_field: str  # Field name for filtering (same as name_field usually)
    order_by_field: str  # Field to order by (job_family, category, tech_stack_name)
    get_master_names_func: Callable  # Function to get master table names
    build_response_func: Callable  # Function to build response from record
    master_table_config: DictType[str, DictType]  # Master table FK configurations
    unique_lookup_fields: List[str]  # Fields to use for finding existing records


# Taxonomy type configurations - defined after helper functions
TAXONOMY_CONFIGS = {
    'role': TaxonomyConfig(
        model_class=RoleTaxonomy,
        response_schema_class=RoleTaxonomyResponse,
        bulk_upsert_item_schema=RoleTaxonomyBulkUpsertItem,
        bulk_upsert_request_schema=RoleTaxonomyBulkUpsertRequest,
        bulk_upsert_response_schema=RoleTaxonomyBulkUpsertResponse,
        bulk_approve_request_schema=RoleTaxonomyBulkApproveRequest,
        bulk_approve_response_schema=RoleTaxonomyBulkApproveResponse,
        delete_response_schema=RoleTaxonomyDeleteResponse,
        list_response_schema=RoleTaxonomyListResponse,
        name_field='job_title',
        name_filter_field='job_title',
        order_by_field='job_family',
        get_master_names_func=get_master_table_names,
        build_response_func=None,  # Will be set dynamically
        master_table_config={
            'occupation': {
                'master_class': MasterCompanyRoleOccupation,
                'field': 'occupation',
                'id_field': 'occupation_id',
                'name_field': 'name'
            },
            'job_family': {
                'master_class': MasterCompanyRoleJobFamily,
                'field': 'job_family',
                'id_field': 'job_family_id',
                'name_field': 'name'
            },
            'job_track': {
                'master_class': MasterCompanyRoleJobTrack,
                'field': 'job_track',
                'id_field': 'job_track_id',
                'name_field': 'name'
            },
            'management_level': {
                'master_class': MasterCompanyRoleManagementLevel,
                'field': 'management_level',
                'id_field': 'management_level_id',
                'name_field': 'name'
            }
        },
        unique_lookup_fields=['job_title', 'job_family', 'occupation']
    ),
    'skill': TaxonomyConfig(
        model_class=SkillTaxonomy,
        response_schema_class=SkillTaxonomyResponse,
        bulk_upsert_item_schema=SkillTaxonomyBulkUpsertItem,
        bulk_upsert_request_schema=SkillTaxonomyBulkUpsertRequest,
        bulk_upsert_response_schema=SkillTaxonomyBulkUpsertResponse,
        bulk_approve_request_schema=SkillTaxonomyBulkApproveRequest,
        bulk_approve_response_schema=SkillTaxonomyBulkApproveResponse,
        delete_response_schema=SkillTaxonomyDeleteResponse,
        list_response_schema=SkillTaxonomyListResponse,
        name_field='skill_name',
        name_filter_field='skill_name',
        order_by_field='category',
        get_master_names_func=get_skill_master_category_names,
        build_response_func=None,
        master_table_config={
            'category': {
                'master_class': MasterSkillTaxonomyCategories,
                'field': 'category',
                'id_field': 'category_id',
                'name_field': 'name'
            }
        },
        unique_lookup_fields=['skill_name']
    ),
    'tech_stack': TaxonomyConfig(
        model_class=TechStackTaxonomy,
        response_schema_class=TechStackTaxonomyResponse,
        bulk_upsert_item_schema=TechStackTaxonomyBulkUpsertItem,
        bulk_upsert_request_schema=TechStackTaxonomyBulkUpsertRequest,
        bulk_upsert_response_schema=TechStackTaxonomyBulkUpsertResponse,
        bulk_approve_request_schema=TechStackTaxonomyBulkApproveRequest,
        bulk_approve_response_schema=TechStackTaxonomyBulkApproveResponse,
        delete_response_schema=TechStackTaxonomyDeleteResponse,
        list_response_schema=TechStackTaxonomyListResponse,
        name_field='tech_stack_name',
        name_filter_field='tech_stack_name',
        order_by_field='tech_stack_name',
        get_master_names_func=get_tech_stack_master_category_names,
        build_response_func=None,
        master_table_config={
            'category': {
                'master_class': MasterTechStackCategory,
                'field': 'category',
                'id_field': 'category_id',
                'name_field': 'name'
            }
        },
        unique_lookup_fields=['tech_stack_name']
    )
}


# ==================== Helper Functions ====================

def get_user_name(user: Optional[User]) -> Optional[str]:
    """Get full name from User object."""
    if user:
        return f"{user.first_name} {user.last_name}".strip()
    return None


def group_records_by_key(
    records: List,
    key_func: callable,
    builder_func: callable
) -> Dict[str, List]:
    """
    Group sorted records by a key function and build response objects.
    
    Args:
        records: List of records sorted by the grouping field
        key_func: Function that extracts the grouping key from a record
        builder_func: Function that builds a response object from a record
    
    Returns:
        Dictionary mapping group keys to lists of response objects
    """
    grouped_data: Dict[str, List] = {}
    for group_key, group_records in groupby(records, key=key_func):
        grouped_data[group_key] = [builder_func(record) for record in group_records]
    return grouped_data


def get_master_table_names(
    db: Session,
    records: List[RoleTaxonomy]
) -> dict:
    """
    Fetch master table names for all FK relationships efficiently.
    
    Returns dict with keys: 'occupation', 'job_family', 'job_track', 'management_level'
    Each contains a dict mapping ID to name.
    """
    master_names = {
        'occupation': {},
        'job_family': {},
        'job_track': {},
        'management_level': {}
    }
    
    occupation_ids = {r.occupation_id for r in records if r.occupation_id}
    job_family_ids = {r.job_family_id for r in records if r.job_family_id}
    job_track_ids = {r.job_track_id for r in records if r.job_track_id}
    management_level_ids = {r.management_level_id for r in records if r.management_level_id}
    
    if occupation_ids:
        occupations = db.query(MasterCompanyRoleOccupation).filter(
            MasterCompanyRoleOccupation.id.in_(occupation_ids)
        ).all()
        master_names['occupation'] = {occ.id: occ.name for occ in occupations}
    
    if job_family_ids:
        job_families = db.query(MasterCompanyRoleJobFamily).filter(
            MasterCompanyRoleJobFamily.id.in_(job_family_ids)
        ).all()
        master_names['job_family'] = {jf.id: jf.name for jf in job_families}
    
    if job_track_ids:
        job_tracks = db.query(MasterCompanyRoleJobTrack).filter(
            MasterCompanyRoleJobTrack.id.in_(job_track_ids)
        ).all()
        master_names['job_track'] = {jt.id: jt.name for jt in job_tracks}
    
    if management_level_ids:
        management_levels = db.query(MasterCompanyRoleManagementLevel).filter(
            MasterCompanyRoleManagementLevel.id.in_(management_level_ids)
        ).all()
        master_names['management_level'] = {ml.id: ml.name for ml in management_levels}
    
    return master_names


def get_skill_master_category_names(
    db: Session,
    records: List[SkillTaxonomy]
) -> dict:
    """
    Fetch master category names for skill taxonomy records efficiently.
    
    Returns dict mapping category_id to category name.
    """
    category_names = {}
    
    category_ids = {record.category_id for record in records if record.category_id}
    
    if category_ids:
        categories = db.query(MasterSkillTaxonomyCategories).filter(
            MasterSkillTaxonomyCategories.id.in_(category_ids)
        ).all()
        category_names = {cat.id: cat.name for cat in categories}
    
    return category_names


def get_tech_stack_master_category_names(
    db: Session,
    records: List[TechStackTaxonomy]
) -> dict:
    """
    Fetch master category names for tech stack taxonomy records efficiently.
    
    Returns dict mapping category_id to category name.
    """
    category_ids = {r.category_id for r in records if r.category_id}
    category_names = {}
    if category_ids:
        categories = db.query(MasterTechStackCategory).filter(
            MasterTechStackCategory.id.in_(category_ids)
        ).all()
        category_names = {cat.id: cat.name for cat in categories}
    return category_names


def bulk_approve_taxonomy_generic(
    db: Session,
    model_class: Type,
    response_class: Type,
    current_user: User,
    request_ids: List[int],
    request_status: Optional[str],
    model_name: str
):
    """
    Generic function to bulk approve taxonomy records.
    
    Works for RoleTaxonomy, SkillTaxonomy, and TechStackTaxonomy.
    """
    if not request_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No IDs provided"
        )
    
    if request_status is None:
        request_status = "approved"
    
    errors = []
    approved_count = 0
    
    records = db.query(model_class).filter(model_class.id.in_(request_ids)).all()
    
    found_ids = {record.id for record in records}
    missing_ids = set(request_ids) - found_ids
    if missing_ids:
        errors.append(f"{model_name} records not found: {', '.join(map(str, missing_ids))}")
    
    for record in records:
        try:
            record.approval_status = request_status
            record.approver_id = current_user.id
            record.modified_by = str(current_user.id)
            
            if request_status == "approved":
                record.approved_on = datetime.utcnow()
            else:
                record.approved_on = None
            
            db.add(record)
            approved_count += 1
        except Exception as e:
            status_action = request_status.lower() if request_status else "updating"
            errors.append(f"Error {status_action} record {record.id}: {str(e)}")
            logger.error(f"Error {status_action} {model_name} {record.id}: {e}", exc_info=True)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        errors.append(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit changes: {str(e)}"
        )
    
    # Generate status-appropriate message
    status_verb = request_status.capitalize() if request_status else "Updated"
    message = f"{status_verb} {approved_count} {model_name} record(s)"
    
    return response_class(
        status="success" if not errors else "partial_success",
        approved_count=approved_count,
        errors=errors,
        message=message
    )


def _remove_role_taxonomy_m2m_links(db: Session, role_taxonomy_ids: List[int]) -> None:
    db.execute(delete(skill_taxonomy_role_association).where(
        skill_taxonomy_role_association.c.role_taxonomy_id.in_(role_taxonomy_ids)
    ))
    db.execute(delete(tech_stack_taxonomy_role_association).where(
        tech_stack_taxonomy_role_association.c.role_taxonomy_id.in_(role_taxonomy_ids)
    ))


def delete_taxonomy_generic(
    db: Session,
    model_class: Type,
    response_class: Type,
    current_user: User,
    taxonomy_id: int,
    model_name: str
):
    record = db.query(model_class).filter(model_class.id == taxonomy_id).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model_name} record with ID {taxonomy_id} not found"
        )
    
    try:
        if model_class is RoleTaxonomy:
            _remove_role_taxonomy_m2m_links(db, [taxonomy_id])
        db.delete(record)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting {model_name} {taxonomy_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete {model_name} record: {str(e)}"
        )
    
    return response_class(
        status="success",
        message=f"{model_name} record {taxonomy_id} deleted successfully",
        deleted_id=taxonomy_id
    )


def bulk_delete_taxonomy_generic(
    db: Session,
    model_class: Type,
    response_class: Type,
    current_user: User,
    request_ids: List[int],
    model_name: str
):
    if not request_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No IDs provided"
        )
    
    errors = []
    deleted_count = 0
    records = db.query(model_class).filter(model_class.id.in_(request_ids)).all()
    found_ids = {record.id for record in records}
    missing_ids = set(request_ids) - found_ids
    if missing_ids:
        errors.append(f"{model_name} records not found: {', '.join(map(str, missing_ids))}")
    
    try:
        if model_class is RoleTaxonomy:
            _remove_role_taxonomy_m2m_links(db, list(found_ids))
        for record in records:
            try:
                db.delete(record)
                deleted_count += 1
            except Exception as e:
                errors.append(f"Error deleting record {record.id}: {str(e)}")
                logger.error(f"Error deleting {model_name} {record.id}: {e}", exc_info=True)
        db.commit()
    except Exception as e:
        db.rollback()
        errors.append(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit changes: {str(e)}"
        )
    
    message = f"Deleted {deleted_count} {model_name} record(s)"
    return response_class(
        status="success" if not errors else "partial_success",
        deleted_count=deleted_count,
        errors=errors,
        message=message
    )


def get_taxonomy_by_company_generic(
    db: Session,
    taxonomy_type: str,
    company_id: int,
    page: int,
    page_size: int,
    status_filter: Optional[str],
    name_filter: Optional[str],
    sort_column: Optional[str] = None,
    sort_type: Optional[str] = None,
    job_titles: Optional[List[str]] = None
):
    """
    Generic function to get taxonomy records by company.
    
    Works for all taxonomy types: role, skill, tech_stack
    """
    config = TAXONOMY_CONFIGS.get(taxonomy_type)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid taxonomy type: {taxonomy_type}"
        )
    
    base_query = db.query(config.model_class).filter(
        config.model_class.company_id == company_id
    )
    
    total_count_query = db.query(config.model_class).filter(
        config.model_class.company_id == company_id
    )
    
    if status_filter:
        base_query = base_query.filter(config.model_class.approval_status == status_filter)
    
    if name_filter:
        name_column = getattr(config.model_class, config.name_filter_field)
        base_query = base_query.filter(name_column.ilike(f"%{name_filter}%"))
        total_count_query = total_count_query.filter(name_column.ilike(f"%{name_filter}%"))
    
    job_title_filter_condition = None
    if job_titles and taxonomy_type in ['skill', 'tech_stack']:
        job_title_ilike_conditions = [RoleTaxonomy.job_title.ilike(f"%{job_title}%") for job_title in job_titles]
        
        if taxonomy_type == 'skill':
            subquery = select(skill_taxonomy_role_association.c.skill_taxonomy_id).join(
                RoleTaxonomy,
                skill_taxonomy_role_association.c.role_taxonomy_id == RoleTaxonomy.id
            ).where(or_(*job_title_ilike_conditions)).distinct().subquery()
            job_title_filter_condition = config.model_class.id.in_(select(subquery.c.skill_taxonomy_id))
        else:
            subquery = select(tech_stack_taxonomy_role_association.c.tech_stack_taxonomy_id).join(
                RoleTaxonomy,
                tech_stack_taxonomy_role_association.c.role_taxonomy_id == RoleTaxonomy.id
            ).where(or_(*job_title_ilike_conditions)).distinct().subquery()
            job_title_filter_condition = config.model_class.id.in_(select(subquery.c.tech_stack_taxonomy_id))
        
        if job_title_filter_condition:
            base_query = base_query.filter(job_title_filter_condition)
            total_count_query = total_count_query.filter(job_title_filter_condition)
    
    total_count = total_count_query.count()
    
    pending_count_query = db.query(config.model_class).filter(
        config.model_class.company_id == company_id,
        config.model_class.approval_status == "pending"
    )
    if name_filter:
        name_column = getattr(config.model_class, config.name_filter_field)
        pending_count_query = pending_count_query.filter(name_column.ilike(f"%{name_filter}%"))
    if job_title_filter_condition:
        pending_count_query = pending_count_query.filter(job_title_filter_condition)
    pending_count = pending_count_query.count()
    
    if sort_column and hasattr(config.model_class, sort_column):
        sort_column_attr = getattr(config.model_class, sort_column)
        if sort_type and sort_type.lower() == 'desc':
            base_query = base_query.order_by(sort_column_attr.desc())
        else:
            base_query = base_query.order_by(sort_column_attr.asc())
        created_on_column = getattr(config.model_class, 'created_on')
        base_query = base_query.order_by(created_on_column.desc())
    else:
        order_by_column = getattr(config.model_class, config.order_by_field)
        created_on_column = getattr(config.model_class, 'created_on')
        base_query = base_query.order_by(
            order_by_column.asc(),
            created_on_column.desc()
        )
    
    paginated_result = paginate(base_query, page=page, page_size=page_size)
    records = paginated_result.items
    
    master_data = config.get_master_names_func(db, records)
    
    user_ids = set()
    for record in records:
        if record.user_id:
            user_ids.add(record.user_id)
        if record.approver_id:
            user_ids.add(record.approver_id)
    
    users_dict = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        users_dict = {user.id: user.username for user in users}
    
    # Handle tech_stack special case - batch fetch tech_stack names
    tech_stack_dict = {}
    if taxonomy_type == 'tech_stack':
        tech_stack_ids = {r.tech_stack_id for r in records if r.tech_stack_id}
        if tech_stack_ids:
            from sqlalchemy.orm import joinedload
            tech_stacks = db.query(MasterTechStack).options(
                joinedload(MasterTechStack.g2_category)
            ).filter(MasterTechStack.id.in_(tech_stack_ids)).all()
            tech_stack_dict = {ts.id: ts.product_name for ts in tech_stacks}
    
    # Batch fetch job_titles for skill and tech_stack taxonomy
    job_titles_dict = {}
    if taxonomy_type in ['skill', 'tech_stack']:
        record_ids = [r.id for r in records]
        if record_ids:
            if taxonomy_type == 'skill':
                stmt = select(
                    skill_taxonomy_role_association.c.skill_taxonomy_id,
                    RoleTaxonomy.job_title
                ).join(
                    RoleTaxonomy,
                    skill_taxonomy_role_association.c.role_taxonomy_id == RoleTaxonomy.id
                ).where(
                    skill_taxonomy_role_association.c.skill_taxonomy_id.in_(record_ids)
                ).distinct()
            else:
                stmt = select(
                    tech_stack_taxonomy_role_association.c.tech_stack_taxonomy_id,
                    RoleTaxonomy.job_title
                ).join(
                    RoleTaxonomy,
                    tech_stack_taxonomy_role_association.c.role_taxonomy_id == RoleTaxonomy.id
                ).where(
                    tech_stack_taxonomy_role_association.c.tech_stack_taxonomy_id.in_(record_ids)
                ).distinct()
            result = db.execute(stmt).fetchall()
            for row in result:
                record_id = row[0]
                job_title = row[1]
                if record_id not in job_titles_dict:
                    job_titles_dict[record_id] = set()
                job_titles_dict[record_id].add(job_title)
            
            for record_id in job_titles_dict:
                job_titles_dict[record_id] = sorted(list(job_titles_dict[record_id]))
    
    # Build response using the response schema
    response_data = []
    for record in records:
        # Use getattr to dynamically access fields
        record_dict = {}
        for field_name in config.response_schema_class.__fields__.keys():
            # Handle special computed fields first
            if field_name == 'approver_username':
                approver_id = getattr(record, 'approver_id', None)
                record_dict[field_name] = users_dict.get(approver_id) if approver_id else None
            elif field_name == 'user_username':
                user_id = getattr(record, 'user_id', None)
                record_dict[field_name] = users_dict.get(user_id) if user_id else None
            elif field_name == 'modified_by_username':
                record_dict[field_name] = getattr(record, 'modified_by', None)
            elif field_name == 'updated_on':
                record_dict[field_name] = getattr(record, 'modified_on', None)
            elif field_name == 'status':
                approval_status = getattr(record, 'approval_status', None)
                if approval_status:
                    record_dict[field_name] = approval_status.value if hasattr(approval_status, 'value') else str(approval_status)
                else:
                    record_dict[field_name] = "pending"
            elif field_name == 'job_titles':
                if taxonomy_type in ['skill', 'tech_stack']:
                    record_dict[field_name] = job_titles_dict.get(record.id, [])
                else:
                    record_dict[field_name] = []
            elif field_name == 'tech_stack_product_name':
                tech_stack_id = getattr(record, 'tech_stack_id', None)
                record_dict[field_name] = tech_stack_dict.get(tech_stack_id) if tech_stack_id else None
            elif field_name == 'category':
                if taxonomy_type == 'skill':
                    if record.category_id and record.category_id in master_data:
                        record_dict[field_name] = master_data[record.category_id]
                    else:
                        record_dict[field_name] = None
                elif taxonomy_type == 'tech_stack':
                    if record.category_id and record.category_id in master_data:
                        record_dict[field_name] = master_data[record.category_id]
                    else:
                        record_dict[field_name] = None
                else:
                    record_dict[field_name] = None
            elif field_name.endswith('_username') and field_name not in ['approver_username', 'user_username', 'modified_by_username']:
                continue
            elif hasattr(record, field_name):
                value = getattr(record, field_name)
                record_dict[field_name] = value
        
        # Handle master table lookups for role taxonomy
        if taxonomy_type == 'role':
            if record.occupation_id and record.occupation_id in master_data.get('occupation', {}):
                record_dict['occupation'] = master_data['occupation'][record.occupation_id]
            if record.job_family_id and record.job_family_id in master_data.get('job_family', {}):
                record_dict['job_family'] = master_data['job_family'][record.job_family_id]
            if record.job_track_id and record.job_track_id in master_data.get('job_track', {}):
                record_dict['job_track'] = master_data['job_track'][record.job_track_id]
            if record.management_level_id and record.management_level_id in master_data.get('management_level', {}):
                record_dict['management_level'] = master_data['management_level'][record.management_level_id]
        
        response_data.append(config.response_schema_class(**record_dict))
    
    return config.list_response_schema(
        data=response_data,
        total_count=total_count,
        pending_count=pending_count,
        page=paginated_result.page,
        page_size=paginated_result.page_size,
        total_pages=paginated_result.total_pages,
        has_next=paginated_result.has_next,
        has_prev=paginated_result.has_prev
    )


def bulk_upsert_taxonomy_generic(
    db: Session,
    taxonomy_type: str,
    request_items: List[Any],
    force_update_flag: bool,
    current_user: User,
    user_company_id: int
):
    """
    Generic function to bulk upsert taxonomy records.
    
    Works for all taxonomy types: role, skill, tech_stack
    Handles FK relationships dynamically using the taxonomy configuration.
    """
    config = TAXONOMY_CONFIGS.get(taxonomy_type)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid taxonomy type: {taxonomy_type}"
        )
    
    company = db.query(MasterCompany).filter(MasterCompany.id == user_company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {user_company_id} does not exist in MasterCompany table."
        )
    
    errors = []
    created_count = 0
    updated_count = 0
    results = []
    
    # Collect usernames to fetch
    usernames_to_fetch = set()
    for item in request_items:
        if hasattr(item, 'user_username') and item.user_username:
            usernames_to_fetch.add(item.user_username)
        if hasattr(item, 'approver_username') and item.approver_username:
            usernames_to_fetch.add(item.approver_username)
        if hasattr(item, 'modified_by_username') and item.modified_by_username:
            usernames_to_fetch.add(item.modified_by_username)
    
    users_by_username = {}
    if usernames_to_fetch:
        users = db.query(User).filter(User.username.in_(usernames_to_fetch)).all()
        users_by_username = {user.username: user for user in users}
        missing_usernames = usernames_to_fetch - set(users_by_username.keys())
        if missing_usernames:
            errors.append(f"Users not found: {', '.join(missing_usernames)}")
    
    # Collect master table values to fetch
    master_values_to_fetch = {key: set() for key in config.master_table_config.keys()}
    for item in request_items:
        for master_key, master_config in config.master_table_config.items():
            field_name = master_config['field']
            if hasattr(item, field_name):
                value = getattr(item, field_name)
                if value:
                    master_values_to_fetch[master_key].add(value)
    
    # Fetch master table IDs
    master_ids_cache = {}
    for master_key, master_config in config.master_table_config.items():
        master_ids_cache[master_key] = {}
        if master_values_to_fetch[master_key]:
            master_class = master_config['master_class']
            name_field = master_config['name_field']
            master_records = db.query(master_class).filter(
                getattr(master_class, name_field).in_(master_values_to_fetch[master_key])
            ).all()
            master_ids_cache[master_key] = {
                getattr(record, name_field): record.id for record in master_records
            }
    
    existing_records_by_id = {}
    existing_records_by_unique = {}
    
    item_ids = [item.id for item in request_items if hasattr(item, 'id') and item.id]
    if item_ids:
        existing_by_id = db.query(config.model_class).filter(
            config.model_class.id.in_(item_ids),
            config.model_class.company_id == user_company_id
        ).all()
        existing_records_by_id = {record.id: record for record in existing_by_id}
    
    unique_lookup_items = []
    for idx, item in enumerate(request_items):
        if not (hasattr(item, 'id') and item.id):
            unique_lookup_items.append((idx, item))
    
    if unique_lookup_items:
        unique_combinations = []
        for idx, item in unique_lookup_items:
            combination = {'company_id': user_company_id}
            for lookup_field in config.unique_lookup_fields:
                if hasattr(item, lookup_field):
                    field_value = getattr(item, lookup_field)
                    combination[lookup_field] = field_value if field_value is not None else ""
                else:
                    combination[lookup_field] = ""
            unique_combinations.append(combination)
        
        if unique_combinations:
            filter_conditions_list = []
            for combo in unique_combinations:
                conditions = [config.model_class.company_id == combo['company_id']]
                for lookup_field in config.unique_lookup_fields:
                    conditions.append(
                        getattr(config.model_class, lookup_field) == combo[lookup_field]
                    )
                filter_conditions_list.append(and_(*conditions))
            
            if filter_conditions_list:
                existing_by_unique = db.query(config.model_class).filter(
                    or_(*filter_conditions_list)
                ).all()
                
                for record in existing_by_unique:
                    key = tuple(
                        getattr(record, field) if getattr(record, field) is not None else ""
                        for field in config.unique_lookup_fields
                    )
                    existing_records_by_unique[key] = record
    
    # Process each item
    for idx, item in enumerate(request_items):
        try:
            # Handle user_id
            user_id = current_user.id
            if hasattr(item, 'user_username') and item.user_username:
                if item.user_username not in users_by_username:
                    errors.append(f"Item {idx}: User '{item.user_username}' not found")
                    continue
                user = users_by_username[item.user_username]
                user_id = user.id
                if user.company_id != user_company_id:
                    errors.append(f"Item {idx}: User '{item.user_username}' belongs to different company")
                    continue
            
            # Handle approver_id
            approver_id = None
            if hasattr(item, 'approver_username') and item.approver_username:
                if item.approver_username not in users_by_username:
                    errors.append(f"Item {idx}: Approver '{item.approver_username}' not found")
                    continue
                approver = users_by_username[item.approver_username]
                approver_id = approver.id
            
            modified_by_username = getattr(item, 'modified_by_username', None) or current_user.username
            
            # Resolve master table FK IDs
            master_fk_ids = {}
            for master_key, master_config in config.master_table_config.items():
                field_name = master_config['field']
                id_field_name = master_config['id_field']
                if hasattr(item, field_name):
                    value = getattr(item, field_name)
                    if value:
                        if value in master_ids_cache[master_key]:
                            master_fk_ids[id_field_name] = master_ids_cache[master_key][value]
                        elif force_update_flag:
                            # Create new master table entry
                            master_class = master_config['master_class']
                            name_field = master_config['name_field']
                            new_master = master_class(**{name_field: value, 'created_by': current_user.username})
                            db.add(new_master)
                            db.flush()
                            master_fk_ids[id_field_name] = new_master.id
                            master_ids_cache[master_key][value] = new_master.id
                        else:
                            errors.append(f"Item {idx}: {master_key} '{value}' not found in master table")
                            continue
            
            # Handle tech_stack_id (direct FK, not master table)
            tech_stack_id = None
            if taxonomy_type == 'tech_stack' and hasattr(item, 'tech_stack_id'):
                tech_stack_id = getattr(item, 'tech_stack_id')
            
            # Find existing record from batch fetch
            existing = None
            if hasattr(item, 'id') and item.id:
                existing = existing_records_by_id.get(item.id)
                if not existing:
                    errors.append(f"Item {idx}: {taxonomy_type} taxonomy record with ID {item.id} not found")
                    continue
            else:
                key = tuple(
                    getattr(item, field) if hasattr(item, field) and getattr(item, field) is not None else ""
                    for field in config.unique_lookup_fields
                )
                existing = existing_records_by_unique.get(key)
            
            # Get master table field names to exclude from direct assignment
            master_field_names = {master_config['field'] for master_config in config.master_table_config.values()}
            master_field_to_id_field = {master_config['field']: master_config['id_field'] for master_config in config.master_table_config.values()}
            
            # Update or create record
            if existing:
                # Update existing record - set all fields dynamically
                for field_name in config.bulk_upsert_item_schema.__fields__.keys():
                    if hasattr(item, field_name) and field_name not in ['id', 'user_username', 'approver_username', 'modified_by_username', 'job_titles']:
                        # Skip master table fields - they're handled via master_fk_ids
                        if field_name in master_field_names:
                            id_field_name = master_field_to_id_field[field_name]
                            if id_field_name in master_fk_ids:
                                setattr(existing, id_field_name, master_fk_ids[id_field_name])
                            continue
                        
                        value = getattr(item, field_name)
                        if hasattr(existing, field_name):
                            if value is not None:
                                setattr(existing, field_name, value)
                            # Handle FK fields
                            id_field_name = f"{field_name}_id"
                            if id_field_name in master_fk_ids:
                                setattr(existing, id_field_name, master_fk_ids[id_field_name])
                
                # Handle tech_stack_id separately
                if taxonomy_type == 'tech_stack' and tech_stack_id is not None:
                    existing.tech_stack_id = tech_stack_id
                
                # Set common fields
                existing.user_id = user_id
                existing.approver_id = approver_id
                existing.modified_by = modified_by_username
                if hasattr(item, 'approval_status') and item.approval_status:
                    existing.approval_status = item.approval_status
                elif hasattr(item, 'status') and item.status:
                    existing.approval_status = item.status
                
                db.add(existing)
                results.append(existing)
                updated_count += 1
            else:
                # Create new record
                record_data = {
                    'company_id': user_company_id,
                    'user_id': user_id,
                    'approver_id': approver_id,
                    'created_by': str(current_user.id),
                    'modified_by': modified_by_username,
                    'approval_status': getattr(item, 'approval_status', getattr(item, 'status', 'pending'))
                }
                
                # Add all item fields dynamically
                for field_name in config.bulk_upsert_item_schema.__fields__.keys():
                    if hasattr(item, field_name) and field_name not in ['id', 'user_username', 'approver_username', 'modified_by_username', 'job_titles']:
                        # Skip master table fields - they're handled via master_fk_ids
                        if field_name in master_field_names:
                            id_field_name = master_field_to_id_field[field_name]
                            if id_field_name in master_fk_ids:
                                record_data[id_field_name] = master_fk_ids[id_field_name]
                            continue
                        
                        value = getattr(item, field_name)
                        # For unique lookup fields that are strings, normalize None to empty string
                        if field_name in config.unique_lookup_fields and value is None:
                            value = ""
                        # Always set unique lookup fields, even if empty string
                        if field_name in config.unique_lookup_fields:
                            record_data[field_name] = value
                        elif value is not None:
                            record_data[field_name] = value
                        # Handle FK fields
                        id_field_name = f"{field_name}_id"
                        if id_field_name in master_fk_ids:
                            record_data[id_field_name] = master_fk_ids[id_field_name]
                
                # Handle tech_stack_id separately
                if taxonomy_type == 'tech_stack' and tech_stack_id is not None:
                    record_data['tech_stack_id'] = tech_stack_id
                
                new_record = config.model_class(**record_data)
                db.add(new_record)
                results.append(new_record)
                created_count += 1
        
        except Exception as e:
            errors.append(f"Item {idx}: {str(e)}")
            logger.error(f"Error processing {taxonomy_type} taxonomy item {idx}: {e}", exc_info=True)
            continue
    
    try:
        db.flush()
        
        if taxonomy_type in ['skill', 'tech_stack']:
            result_ids = [r.id for r in results]
            result_id_to_result = {r.id: idx for idx, r in enumerate(results)}
            
            existing_associations = {}
            if result_ids:
                if taxonomy_type == 'skill':
                    existing_stmt = select(
                        skill_taxonomy_role_association.c.skill_taxonomy_id,
                        skill_taxonomy_role_association.c.role_taxonomy_id
                    ).where(
                        skill_taxonomy_role_association.c.skill_taxonomy_id.in_(result_ids)
                    )
                else:
                    existing_stmt = select(
                        tech_stack_taxonomy_role_association.c.tech_stack_taxonomy_id,
                        tech_stack_taxonomy_role_association.c.role_taxonomy_id
                    ).where(
                        tech_stack_taxonomy_role_association.c.tech_stack_taxonomy_id.in_(result_ids)
                    )
                
                existing_result = db.execute(existing_stmt).fetchall()
                for row in existing_result:
                    taxonomy_id = row[0]
                    role_taxonomy_id = row[1]
                    if taxonomy_id not in existing_associations:
                        existing_associations[taxonomy_id] = set()
                    existing_associations[taxonomy_id].add(role_taxonomy_id)
            
            all_job_titles = set()
            items_with_job_titles = []
            for idx, result in enumerate(results):
                item = request_items[idx]
                job_titles = getattr(item, 'job_titles', None)
                if job_titles:
                    all_job_titles.update(job_titles)
                    items_with_job_titles.append((result, job_titles, result.company_id))
            
            role_taxonomy_map = {}
            if all_job_titles and items_with_job_titles:
                company_ids = {item[2] for item in items_with_job_titles}
                role_taxonomies = db.query(RoleTaxonomy).filter(
                    RoleTaxonomy.company_id.in_(company_ids),
                    RoleTaxonomy.job_title.in_(all_job_titles)
                ).all()
                for rt in role_taxonomies:
                    key = (rt.company_id, rt.job_title)
                    if key not in role_taxonomy_map:
                        role_taxonomy_map[key] = []
                    role_taxonomy_map[key].append(rt.id)
                desired_role_keys = set()
                for _result, job_titles_list, company_id in items_with_job_titles:
                    for job_title in job_titles_list:
                        desired_role_keys.add((company_id, job_title))
                for company_id, job_title in desired_role_keys:
                    key = (company_id, job_title)
                    if key not in role_taxonomy_map or not role_taxonomy_map[key]:
                        existing = db.query(RoleTaxonomy).filter(
                            RoleTaxonomy.company_id == company_id,
                            RoleTaxonomy.job_title == job_title,
                            RoleTaxonomy.job_family == "",
                            RoleTaxonomy.occupation == ""
                        ).first()
                        if existing:
                            if key not in role_taxonomy_map:
                                role_taxonomy_map[key] = []
                            role_taxonomy_map[key].append(existing.id)
                        else:
                            new_role = RoleTaxonomy(
                                company_id=company_id,
                                job_title=job_title or "",
                                job_family="",
                                occupation="",
                                user_id=current_user.id,
                                source="User"
                            )
                            db.add(new_role)
                            db.flush()
                            if key not in role_taxonomy_map:
                                role_taxonomy_map[key] = []
                            role_taxonomy_map[key].append(new_role.id)
            
            all_deletes = []
            all_inserts = []
            
            for result, job_titles, company_id in items_with_job_titles:
                existing_role_ids = existing_associations.get(result.id, set())
                
                desired_role_ids = set()
                for job_title in job_titles:
                    key = (company_id, job_title)
                    if key in role_taxonomy_map:
                        desired_role_ids.update(role_taxonomy_map[key])
                
                role_ids_to_delete = existing_role_ids - desired_role_ids
                role_ids_to_add = desired_role_ids - existing_role_ids
                
                if role_ids_to_delete:
                    if taxonomy_type == 'skill':
                        all_deletes.append({
                            'skill_taxonomy_id': result.id,
                            'role_taxonomy_ids': list(role_ids_to_delete)
                        })
                    else:
                        all_deletes.append({
                            'tech_stack_taxonomy_id': result.id,
                            'role_taxonomy_ids': list(role_ids_to_delete)
                        })
                
                if role_ids_to_add:
                    if taxonomy_type == 'skill':
                        for role_id in role_ids_to_add:
                            all_inserts.append({
                                'skill_taxonomy_id': result.id,
                                'role_taxonomy_id': role_id
                            })
                    else:
                        for role_id in role_ids_to_add:
                            all_inserts.append({
                                'tech_stack_taxonomy_id': result.id,
                                'role_taxonomy_id': role_id
                            })
            
            if all_deletes:
                if taxonomy_type == 'skill':
                    for delete_item in all_deletes:
                        db.execute(
                            skill_taxonomy_role_association.delete().where(
                                skill_taxonomy_role_association.c.skill_taxonomy_id == delete_item['skill_taxonomy_id'],
                                skill_taxonomy_role_association.c.role_taxonomy_id.in_(delete_item['role_taxonomy_ids'])
                            )
                        )
                else:
                    for delete_item in all_deletes:
                        db.execute(
                            tech_stack_taxonomy_role_association.delete().where(
                                tech_stack_taxonomy_role_association.c.tech_stack_taxonomy_id == delete_item['tech_stack_taxonomy_id'],
                                tech_stack_taxonomy_role_association.c.role_taxonomy_id.in_(delete_item['role_taxonomy_ids'])
                            )
                        )
            
            if all_inserts:
                if taxonomy_type == 'skill':
                    for row in all_inserts:
                        db.execute(skill_taxonomy_role_association.insert().values(**row))
                else:
                    for row in all_inserts:
                        db.execute(tech_stack_taxonomy_role_association.insert().values(**row))
        
        db.commit()
    except Exception as e:
        db.rollback()
        errors.append(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit changes: {str(e)}"
        )
    
    # Build response data
    master_data = config.get_master_names_func(db, results)
    
    users_dict = {}
    user_ids = set()
    for result in results:
        if result.user_id:
            user_ids.add(result.user_id)
        if result.approver_id:
            user_ids.add(result.approver_id)
    
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        users_dict = {user.id: user.username for user in users}
    
    job_titles_dict = {}
    if taxonomy_type in ['skill', 'tech_stack'] and results:
        result_ids = [r.id for r in results]
        if taxonomy_type == 'skill':
            stmt = select(
                skill_taxonomy_role_association.c.skill_taxonomy_id,
                RoleTaxonomy.job_title
            ).join(
                RoleTaxonomy,
                skill_taxonomy_role_association.c.role_taxonomy_id == RoleTaxonomy.id
            ).where(
                skill_taxonomy_role_association.c.skill_taxonomy_id.in_(result_ids)
            ).distinct()
        else:
            stmt = select(
                tech_stack_taxonomy_role_association.c.tech_stack_taxonomy_id,
                RoleTaxonomy.job_title
            ).join(
                RoleTaxonomy,
                tech_stack_taxonomy_role_association.c.role_taxonomy_id == RoleTaxonomy.id
            ).where(
                tech_stack_taxonomy_role_association.c.tech_stack_taxonomy_id.in_(result_ids)
            ).distinct()
        assoc_result = db.execute(stmt).fetchall()
        for row in assoc_result:
            tid, job_title = row[0], row[1]
            if tid not in job_titles_dict:
                job_titles_dict[tid] = []
            if job_title and job_title not in job_titles_dict[tid]:
                job_titles_dict[tid].append(job_title)
        for tid in job_titles_dict:
            job_titles_dict[tid] = sorted(job_titles_dict[tid])
    
    tech_stack_dict = {}
    if taxonomy_type == 'tech_stack':
        tech_stack_ids = {r.tech_stack_id for r in results if r.tech_stack_id}
        if tech_stack_ids:
            from sqlalchemy.orm import joinedload
            tech_stacks = db.query(MasterTechStack).options(
                joinedload(MasterTechStack.g2_category)
            ).filter(MasterTechStack.id.in_(tech_stack_ids)).all()
            tech_stack_dict = {ts.id: ts.product_name for ts in tech_stacks}
    
    response_schema = config.response_schema_class
    response_fields = getattr(response_schema, "model_fields", None) or getattr(response_schema, "__fields__", None)
    if response_fields is None:
        response_fields = response_schema.__annotations__
    field_names = list(response_fields.keys()) if hasattr(response_fields, "keys") else list(response_fields)
    response_data = []
    for record in results:
        record_dict = {}
        for field_name in field_names:
            # Handle special computed fields first
            if field_name == 'approver_username':
                approver_id = getattr(record, 'approver_id', None)
                record_dict[field_name] = users_dict.get(approver_id) if approver_id else None
            elif field_name == 'user_username':
                user_id = getattr(record, 'user_id', None)
                record_dict[field_name] = users_dict.get(user_id) if user_id else None
            elif field_name == 'modified_by_username':
                record_dict[field_name] = getattr(record, 'modified_by', None)
            elif field_name == 'updated_on':
                record_dict[field_name] = getattr(record, 'modified_on', None)
            elif field_name == 'status':
                approval_status = getattr(record, 'approval_status', None)
                if approval_status:
                    record_dict[field_name] = approval_status.value if hasattr(approval_status, 'value') else str(approval_status)
                else:
                    record_dict[field_name] = "pending"
            elif field_name == 'job_titles':
                if taxonomy_type in ['skill', 'tech_stack']:
                    record_dict[field_name] = job_titles_dict.get(record.id, [])
                else:
                    record_dict[field_name] = []
            elif field_name == 'tech_stack_product_name':
                tech_stack_id = getattr(record, 'tech_stack_id', None)
                record_dict[field_name] = tech_stack_dict.get(tech_stack_id) if tech_stack_id else None
            elif field_name == 'category':
                if taxonomy_type == 'skill':
                    if hasattr(record, 'category_id') and record.category_id and record.category_id in master_data:
                        record_dict[field_name] = master_data[record.category_id]
                    else:
                        record_dict[field_name] = None
                elif taxonomy_type == 'tech_stack':
                    if hasattr(record, 'category_id') and record.category_id and record.category_id in master_data:
                        record_dict[field_name] = master_data[record.category_id]
                    else:
                        record_dict[field_name] = None
                else:
                    record_dict[field_name] = None
            elif field_name.endswith('_username') and field_name not in ['approver_username', 'user_username', 'modified_by_username']:
                continue
            elif hasattr(record, field_name):
                value = getattr(record, field_name)
                record_dict[field_name] = value
        
        if taxonomy_type == "role":
            for master_key in ["occupation", "job_family", "job_track", "management_level"]:
                id_field = f"{master_key}_id"
                if hasattr(record, id_field) and getattr(record, id_field):
                    master_id = getattr(record, id_field)
                    if master_id in master_data.get(master_key, {}):
                        record_dict[master_key] = master_data[master_key][master_id]
        if taxonomy_type in ["skill", "tech_stack"]:
            if "status" not in record_dict:
                approval_status = getattr(record, "approval_status", None)
                if approval_status:
                    record_dict["status"] = approval_status.value if hasattr(approval_status, "value") else str(approval_status)
                else:
                    record_dict["status"] = "pending"
            if "job_titles" not in record_dict:
                record_dict["job_titles"] = job_titles_dict.get(record.id, [])

        response_data.append(config.response_schema_class(**record_dict))
    
    return config.bulk_upsert_response_schema(
        status="success" if not errors else "partial_success",
        data=response_data,
        total_count=len(response_data),
        created_count=created_count,
        updated_count=updated_count,
        errors=errors
    )


def ensure_user_exists(db: Session, draup_user: ResponseModel) -> User:
    """
    Ensure user exists in local database, create if not exists.
    
    Returns the User object from local database.
    """
    if draup_user.status != "Success" or not draup_user.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
    
    user_data = draup_user.data
    
    if not user_data.get("email"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not found in user data"
        )
    
    # Check if user exists in local DB
    user_obj = db.query(User).filter(User.email == user_data["email"]).first()
    
    if not user_obj:
        # Create user if doesn't exist
        if "group" not in user_data:
            user_data["group"] = "Admin"
        
        create_result = create_user(db, user_data)
        if create_result.get("status").lower() != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {create_result.get('error')}"
            )
        
        user_obj = create_result["data"]
        logger.info(f"Created new user in local DB: {user_obj.id} ({user_obj.email})")
    
    return user_obj


class UpdateDocumentDataRequest(BaseModel):
    """Request to update extracted data for a document."""
    session_id: UUID = Field(..., description="Session ID for validation")
    tasks: Optional[list] = Field(None, description="Updated tasks list")
    skills: Optional[list] = Field(None, description="Updated skills list")
    stages: Optional[list] = Field(None, description="Updated stages list")
    task_to_skill: Optional[list] = Field(None, description="Updated task-to-skill mappings")


class UpdateDocumentDataResponse(BaseModel):
    """Response after updating document data."""
    document_id: str
    session_id: str
    message: str
    updated_fields: list
    approval_status: str
    updated_at: datetime


# ==================== Endpoints ====================

@extraction_router.post("/session", response_model=CreateSessionResponse)
async def create_session(
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Create a new extraction session.

    A session groups multiple documents for extraction and allows
    monitoring progress even after page refresh.
    """
    try:
        # Ensure user exists in local DB
        user = db.query(User).filter(User.email == draup_user.data.get("email")).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        logger.info(f"Creating extraction session for user {user.id}")
        
        session = ExtractionSession(
            user_id=user.id,
            status=ExtractionSessionStatus.ACTIVE
        )
        logger.info(f"Session object created with id: {session.id}")
        
        db.add(session)
        logger.info("Session added to db")
        
        db.commit()
        logger.info("Session committed to db")
        
        db.refresh(session)
        logger.info(f"Created extraction session {session.id} for user {user.id}")

        # Get user name
        user_name = user.username

        return CreateSessionResponse(
            session_id=str(session.id),
            status=session.status.value,
            user_name=user_name,
            created_at=session.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@extraction_router.post("/process", response_model=ProcessDocumentResponse)
async def process_document(
    request: ProcessDocumentRequest,
    background_tasks: BackgroundTasks,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """
    Initiate extraction for one or more documents.

    Documents are processed sequentially in the background.
    Accepts 1-5 document IDs per request.
    """
    try:
        user = ensure_user_exists(db, draup_user)
        tenant_id = str(draup_user.data.get("company_id", ""))
        
        session = db.query(ExtractionSession).filter(
            ExtractionSession.id == request.session_id,
            ExtractionSession.user_id == user.id
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )

        if session.status != ExtractionSessionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session is {session.status.value}, cannot add documents"
            )

        existing_docs = db.query(Document).filter(
            Document.id.in_(request.document_ids),
            Document.tenant_id == tenant_id,
            Document.status.notin_([DocumentStatus.DELETED, DocumentStatus.ABORTED])
        ).all()

        existing_doc_ids = {doc.id for doc in existing_docs}

        records = []
        for doc_id in request.document_ids:
            if doc_id not in existing_doc_ids:
                records.append(DocumentRecordInfo(
                    document_id=str(doc_id),
                    record_id=-1,
                    status="VALIDATION_FAILED",
                    error="Document not found or not accessible"
                ))
                logger.warning(f"Document {doc_id} not found for tenant {tenant_id}")
                continue

            extracted_doc = ExtractedDocument(
                session_id=request.session_id,
                document_id=doc_id,
                document_name=None,
                document_type=None,
                status=ExtractionStatus.PENDING,
                approval_status=ApprovalStatus.PENDING,
                created_by=str(user.id),
                modified_on=datetime.utcnow()
            )
            db.add(extracted_doc)
            db.flush()

            records.append(DocumentRecordInfo(
                document_id=str(doc_id),
                record_id=extracted_doc.id,
                status=ExtractionStatus.PENDING.value,
                error=None
            ))

            logger.info(f"Created extraction record {extracted_doc.id} for document {doc_id}")

        db.commit()

        valid_record_ids = [r.record_id for r in records if r.record_id > 0]

        if valid_record_ids:
            background_tasks.add_task(
                _run_batch_extraction,
                extracted_doc_ids=valid_record_ids,
                tenant_id=tenant_id
            )

        message = f"Extraction started for {len(valid_record_ids)} document(s)"
        if len(valid_record_ids) != len(request.document_ids):
            failed_count = len(request.document_ids) - len(valid_record_ids)
            message += f" ({failed_count} validation failed)"

        return ProcessDocumentResponse(
            session_id=str(request.session_id),
            total_documents=len(request.document_ids),
            records=records,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


@extraction_router.get("/session/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: UUID,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Get status of an extraction session with all documents.

    Returns the session status and list of all documents with their
    extraction status, results, and approval status.
    """
    try:
        user = ensure_user_exists(db, draup_user)
        
        session = db.query(ExtractionSession).filter(
            ExtractionSession.id == session_id,
            ExtractionSession.user_id == user.id
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )

        documents = [
            ExtractedDocumentResponse(
                id=doc.id,
                document_id=str(doc.document_id),
                document_name=doc.document_name,
                status=doc.status.value,
                document_type=doc.document_type,
                extraction_confidence=doc.extraction_confidence,
                tasks=doc.tasks,
                skills=doc.skills,
                stages=doc.stages,
                roles=doc.roles,
                approval_status=doc.approval_status.value,
                error_message=doc.error_message,
                created_on=doc.created_on,
                modified_on=doc.modified_on
            )
            for doc in session.documents
        ]

        doc_counts = {
            "total": len(session.documents),
            "pending": sum(1 for d in session.documents if d.status == ExtractionStatus.PENDING),
            "processing": sum(1 for d in session.documents if d.status == ExtractionStatus.PROCESSING),
            "completed": sum(1 for d in session.documents if d.status == ExtractionStatus.COMPLETED),
            "failed": sum(1 for d in session.documents if d.status == ExtractionStatus.FAILED)
        }

        can_complete = (
            session.status == ExtractionSessionStatus.ACTIVE and
            len(session.documents) > 0 and
            all(doc.status in (ExtractionStatus.COMPLETED, ExtractionStatus.FAILED)
                for doc in session.documents)
        )

        user_obj = db.query(User).filter(User.id == session.user_id).first()
        user_name = user_obj.username if user_obj else None
        
        approver_name = None
        if session.approver_id:
            approver = db.query(User).filter(User.id == session.approver_id).first()
            approver_name = approver.username if approver else None

        return SessionStatusResponse(
            session_id=str(session.id),
            status=session.status.value,
            user_name=user_name,
            approver_name=approver_name,
            created_at=session.created_at,
            updated_at=session.updated_at,
            documents=documents,
            can_complete=can_complete,
            statistics=doc_counts
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session status {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session status: {str(e)}"
        )


@extraction_router.post("/document/{record_id}/approve", response_model=ApprovalResponse)
async def approve_document(
    record_id: int,
    request: ApprovalRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Approve or reject an extracted document.

    Only completed extractions can be approved/rejected.
    """
    try:
        user = ensure_user_exists(db, draup_user)
        
        extracted_doc = db.query(ExtractedDocument).join(ExtractionSession).filter(
            ExtractedDocument.id == record_id,
            ExtractionSession.user_id == user.id
        ).first()

        if not extracted_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied"
            )

        if extracted_doc.status != ExtractionStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve document with status {extracted_doc.status.value}"
            )

        extracted_doc.approval_status = request.approval_status
        extracted_doc.approver_id = user.id
        extracted_doc.modified_by = str(user.id)
        
        if request.approval_status == ApprovalStatus.APPROVED:
            extracted_doc.approved_on = datetime.utcnow()
        else:
            extracted_doc.approved_on = None
        
        db.commit()

        logger.info(
            f"Document {record_id} approval updated to {request.approval_status.value} "
            f"by user {user.id}"
        )

        return ApprovalResponse(
            record_id=record_id,
            approval_status=extracted_doc.approval_status.value,
            approved_at=extracted_doc.approved_on,
            message=f"Document {request.approval_status.value.lower()}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving document {record_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve document: {str(e)}"
        )


@extraction_router.post("/session/{session_id}/approve", response_model=SessionApprovalResponse)
async def approve_session(
    session_id: UUID,
    request: ApprovalRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Approve or reject all documents in a session.

    All documents in the session must be COMPLETED before approval/rejection.
    This applies the approval status to ALL documents in the session.
    """
    try:
        user = ensure_user_exists(db, draup_user)
        
        session = db.query(ExtractionSession).filter(
            ExtractionSession.id == session_id,
            ExtractionSession.user_id == user.id
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )

        documents = session.documents

        if not documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session has no documents"
            )

        non_completed = [
            doc for doc in documents
            if doc.status != ExtractionStatus.COMPLETED
        ]

        if non_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve session: {len(non_completed)} document(s) not completed"
            )

        approval_time = datetime.utcnow()
        for doc in documents:
            doc.approval_status = request.approval_status
            doc.approver_id = user.id
            doc.modified_by = str(user.id)
            
            if request.approval_status == ApprovalStatus.APPROVED:
                doc.approved_on = approval_time
            else:
                doc.approved_on = None

        session.approver_id = user.id
        session.approved_at = approval_time

        db.commit()

        logger.info(
            f"Session {session_id} approval updated to {request.approval_status.value} "
            f"for {len(documents)} document(s) by user {user.id}"
        )

        user_obj = db.query(User).filter(User.id == session.user_id).first()
        user_name = user_obj.username if user_obj else None
        
        approver = db.query(User).filter(User.id == session.approver_id).first()
        approver_name = approver.username if approver else None

        return SessionApprovalResponse(
            session_id=str(session_id),
            total_documents=len(documents),
            approval_status=request.approval_status.value,
            user_name=user_name,
            approver_name=approver_name,
            approved_at=approval_time,
            message=f"All {len(documents)} document(s) {request.approval_status.value.lower()}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving session {session_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve session: {str(e)}"
        )


@extraction_router.post("/session/{session_id}/complete", response_model=CompleteSessionResponse)
async def complete_session(
    session_id: UUID,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Manually complete an extraction session.

    Once completed, the session becomes immutable - no more documents can be added.
    All documents must be in terminal state (COMPLETED or FAILED) before completion.

    Requirements:
    - Session must be ACTIVE
    - All documents must be COMPLETED or FAILED
    - Session must belong to authenticated user
    """
    try:
        user = ensure_user_exists(db, draup_user)
        
        session = db.query(ExtractionSession).filter(
            ExtractionSession.id == session_id,
            ExtractionSession.user_id == user.id
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )

        if session.status != ExtractionSessionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session is already {session.status.value}, cannot complete"
            )

        documents = session.documents

        if not documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot complete session with no documents"
            )

        non_terminal = [
            doc for doc in documents
            if doc.status not in (ExtractionStatus.COMPLETED, ExtractionStatus.FAILED)
        ]

        if non_terminal:
            non_terminal_statuses = [doc.status.value for doc in non_terminal]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot complete session: {len(non_terminal)} document(s) still processing. "
                       f"Statuses: {', '.join(set(non_terminal_statuses))}"
            )

        completed_count = sum(1 for doc in documents if doc.status == ExtractionStatus.COMPLETED)
        failed_count = sum(1 for doc in documents if doc.status == ExtractionStatus.FAILED)

        session.status = ExtractionSessionStatus.COMPLETED
        completed_at = datetime.utcnow()
        session.updated_at = completed_at

        db.commit()

        logger.info(
            f"Session {session_id} manually completed by user {user.id}. "
            f"Total: {len(documents)}, Completed: {completed_count}, Failed: {failed_count}"
        )

        session_user = db.query(User).filter(User.id == session.user_id).first()
        user_name = session_user.username if session_user else None
        
        approver_name = None
        if session.approver_id:
            approver = db.query(User).filter(User.id == session.approver_id).first()
            approver_name = approver.username if approver else None

        return CompleteSessionResponse(
            session_id=str(session_id),
            status=session.status.value,
            user_name=user_name,
            approver_name=approver_name,
            completed_at=completed_at,
            total_documents=len(documents),
            completed_count=completed_count,
            failed_count=failed_count,
            message=f"Session completed with {completed_count} successful and {failed_count} failed extraction(s)"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing session {session_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete session: {str(e)}"
        )


@extraction_router.put("/session/{session_id}/update", response_model=UpdateSessionResponse)
async def update_session(
    session_id: UUID,
    request: UpdateSessionRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Update extraction session status and/or approver.
    
    Updates the session status and/or sets the approver by username.
    If approver_username is provided, looks up the user by username and sets approver_id.
    """
    try:
        user = db.query(User).filter(User.email == draup_user.data.get("email")).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        session = db.query(ExtractionSession).filter(
            ExtractionSession.id == session_id,
            ExtractionSession.user_id == user.id
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )

        if request.status is not None:
            session.status = request.status
            logger.info(f"Updating session {session_id} status to {request.status.value}")

        approver = None
        approver_id = None
        if request.approver_username is not None:
            approver = db.query(User).filter(User.username == request.approver_username).first()
            if not approver:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Approver with username '{request.approver_username}' not found"
                )
            session.approver_id = approver.id
            approver_id = approver.id
            session.approved_at = datetime.utcnow()
            logger.info(f"Setting approver for session {session_id} to user {approver.id} ({approver.username})")

        session.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(session)

        session_user = db.query(User).filter(User.id == session.user_id).first()
        user_name = session_user.username if session_user else None
        
        approver_name = None
        if session.approver_id:
            approver_user = db.query(User).filter(User.id == session.approver_id).first()
            approver_name = approver_user.username if approver_user else None

        updates = []
        if request.status is not None:
            updates.append(f"status to {request.status.value}")
        if request.approver_username is not None:
            updates.append(f"approver to {request.approver_username}")
        message = f"Session updated: {', '.join(updates)}" if updates else "Session updated"

        logger.info(f"Updated session {session_id} by user {user.id}")

        return UpdateSessionResponse(
            session_id=str(session_id),
            status=session.status.value,
            user_name=user_name,
            approver_name=approver_name,
            approver_id=approver_id or session.approver_id,
            updated_at=session.updated_at,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session {session_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session: {str(e)}"
        )


def _get_content_type_filter(content_type: str):
    """
    Convert generic content type values to MIME type patterns for filtering.
    
    Handles generic types like 'pdf', 'png', 'csv', 'txt', 'image', 'excel' and maps them
    to their corresponding MIME type patterns or exact matches.
    
    Args:
        content_type: Generic type (e.g., 'pdf', 'png') or full MIME type (e.g., 'application/pdf')
    
    Returns:
        List of MIME type patterns to match against
    """
    content_type_lower = content_type.lower().strip()
    
    type_mapping = {
        'pdf': ['application/pdf'],
        'png': ['image/png'],
        'jpg': ['image/jpeg', 'image/jpg'],
        'jpeg': ['image/jpeg', 'image/jpg'],
        'csv': ['text/csv', 'application/csv'],
        'txt': ['text/plain'],
        'text': ['text/plain'],
        'image': ['image/jpeg', 'image/jpg', 'image/png'],
        'excel': ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'text/csv', 'application/csv'],
        'doc': ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        'xls': ['application/vnd.ms-excel'],
        'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        'ppt': ['application/vnd.ms-powerpoint'],
        'pptx': ['application/vnd.openxmlformats-officedocument.presentationml.presentation'],
        'json': ['application/json'],
        'xml': ['application/xml', 'text/xml']
    }
    
    if content_type_lower in type_mapping:
        return type_mapping[content_type_lower]
    
    if '/' in content_type:
        return [content_type]
    
    return [f'%{content_type_lower}%']


@extraction_router.get("/files", response_model=CompanyFilesListResponse)
async def list_company_files(
    company_instance_name: Optional[str] = Query(None, description="Filter by company instance name"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    content_type: Optional[str] = Query(None, description="Filter by content type (e.g., pdf, png, csv, txt, image)"),
    roles: Optional[str] = Query(None, description="Filter by role (checks if roles JSONB contains this value)"),
    status: Optional[str] = Query(None, description="Filter by extraction status (PENDING, PROCESSING, COMPLETED, FAILED)"),
    search: Optional[str] = Query(None, description="Search in filename (case-insensitive contains)"),
    sort_column: Optional[str] = Query(None, description="Sort by column: document_type, file_name, last_modified_at"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    List all uploaded files for the company (tenant) that have completed extraction.

    Returns all S3 documents for the authenticated user's tenant
    that have been successfully extracted.
    Optionally filters by document_type, content_type, roles, status, and/or company_instance_name if provided.
    Supports pagination and sorting.
    
    Content type filter supports:
    - Generic types: pdf, png, jpg, jpeg, csv, txt, image, excel, doc, docx, xls, xlsx, ppt, pptx, json, xml
    - Full MIME types: application/pdf, image/png, text/csv, etc.
    - Note: 'excel' includes both Excel formats (xls, xlsx) and CSV files
    
    Status filter supports: PENDING, PROCESSING, COMPLETED, FAILED
    
    Sort options:
    - sort_column: document_type, file_name, last_modified_at
    - sort_order: asc or desc (default: desc)
    """
    try:
        user = ensure_user_exists(db, draup_user)
        tenant_id = str(draup_user.data.get("company_id", ""))
        
        base_query = db.query(Document).join(
            ExtractedDocument,
            Document.id == ExtractedDocument.document_id
        ).filter(
            Document.tenant_id == tenant_id,
            Document.status.notin_([DocumentStatus.DELETED, DocumentStatus.ABORTED])
        )
        
        if not status:
            base_query = base_query.filter(ExtractedDocument.status == ExtractionStatus.COMPLETED)
        elif status:
            try:
                status_enum = ExtractionStatus[status.upper()]
                base_query = base_query.filter(ExtractedDocument.status == status_enum)
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status value. Must be one of: {', '.join([s.name for s in ExtractionStatus])}"
                )
        
        if company_instance_name:
            base_query = base_query.filter(Document.company_instance_name == company_instance_name)
        
        if document_type:
            base_query = base_query.filter(ExtractedDocument.document_type == document_type)
        
        if content_type:
            content_type_patterns = _get_content_type_filter(content_type)
            conditions = []
            
            for pattern in content_type_patterns:
                if pattern.startswith('%'):
                    conditions.append(
                        (Document.observed_content_type.ilike(pattern)) |
                        (Document.declared_content_type.ilike(pattern))
                    )
                else:
                    conditions.append(
                        (Document.observed_content_type == pattern) |
                        (Document.declared_content_type == pattern)
                    )
            
            if conditions:
                base_query = base_query.filter(or_(*conditions))
        
        if roles:
            role_array = json.dumps([roles])
            base_query = base_query.filter(
                ExtractedDocument.roles.op('@>')(cast(role_array, JSONB))
            )
        
        if search:
            base_query = base_query.filter(
                Document.original_filename.ilike(f'%{search}%')
            )
        
        if sort_column:
            sort_order_lower = (sort_order or "desc").lower()
            if sort_column == "document_type":
                if sort_order_lower == "asc":
                    base_query = base_query.order_by(ExtractedDocument.document_type.asc(), Document.created_at.desc())
                else:
                    base_query = base_query.order_by(ExtractedDocument.document_type.desc(), Document.created_at.desc())
            elif sort_column == "file_name":
                if sort_order_lower == "asc":
                    base_query = base_query.order_by(Document.original_filename.asc(), Document.created_at.desc())
                else:
                    base_query = base_query.order_by(Document.original_filename.desc(), Document.created_at.desc())
            elif sort_column == "last_modified_at":
                if sort_order_lower == "asc":
                    base_query = base_query.order_by(Document.created_at.asc())
                else:
                    base_query = base_query.order_by(Document.created_at.desc())
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid sort_column. Must be one of: document_type, file_name, last_modified_at"
                )
        else:
            base_query = base_query.order_by(Document.created_at.desc())
        
        paginated_result = paginate(base_query, page=page, page_size=page_size)
        
        document_ids = [doc.id for doc in paginated_result.items]
        
        if sort_column:
            sort_order_lower = (sort_order or "desc").lower()
            if sort_column == "document_type":
                if sort_order_lower == "asc":
                    order_by_clause = [ExtractedDocument.document_type.asc(), Document.created_at.desc()]
                else:
                    order_by_clause = [ExtractedDocument.document_type.desc(), Document.created_at.desc()]
            elif sort_column == "file_name":
                if sort_order_lower == "asc":
                    order_by_clause = [Document.original_filename.asc(), Document.created_at.desc()]
                else:
                    order_by_clause = [Document.original_filename.desc(), Document.created_at.desc()]
            elif sort_column == "last_modified_at":
                if sort_order_lower == "asc":
                    order_by_clause = [Document.created_at.asc()]
                else:
                    order_by_clause = [Document.created_at.desc()]
            else:
                order_by_clause = [Document.created_at.desc()]
        else:
            order_by_clause = [Document.created_at.desc()]
        
        query = db.query(Document, ExtractedDocument).join(
            ExtractedDocument,
            Document.id == ExtractedDocument.document_id
        ).filter(Document.id.in_(document_ids)).order_by(*order_by_clause)
        
        results = query.all()

        files = []
        for doc, extraction in results:
            files.append(CompanyFileResponse(
                id=extraction.id,
                document_id=str(doc.id),
                original_filename=doc.original_filename,
                document_status=doc.status.value,
                content_type=doc.observed_content_type or doc.declared_content_type,
                size_bytes=doc.observed_size_bytes or doc.declared_size_bytes,
                created_at=doc.created_at,
                folder_path=doc.folder_path,
                has_extraction=True,
                extraction_status=extraction.status.value,
                approval_status=extraction.approval_status.value,
                document_type=extraction.document_type,
                last_modified_at=get_minimized_time_ago(doc.created_at)
            ))

        return CompanyFilesListResponse(
            tenant_id=tenant_id,
            total_count=paginated_result.total,
            files=files,
            page=paginated_result.page,
            page_size=paginated_result.page_size,
            total_pages=paginated_result.total_pages,
            has_next=paginated_result.has_next,
            has_prev=paginated_result.has_prev
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing company files: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list company files: {str(e)}"
        )


@extraction_router.post("/files/bulk_approve", response_model=ExtractedDocumentBulkApproveResponse)
async def bulk_approve_extracted_documents(
    request: ExtractedDocumentBulkApproveRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Bulk update extracted document approval status.
    
    Accepts a list of extracted document IDs and updates their approval_status.
    Defaults to 'approved' if status is not provided.
    """
    try:
        user = ensure_user_exists(db, draup_user)
        tenant_id = str(draup_user.data.get("company_id", ""))
        
        if not request.ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No IDs provided"
            )
        
        request_status = request.status or "approved"
        
        if request_status not in ["PENDING", "APPROVED", "REJECTED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status. Must be one of: PENDING, APPROVED, REJECTED"
            )
        
        errors = []
        approved_count = 0
        
        records = db.query(ExtractedDocument).join(
            Document,
            ExtractedDocument.document_id == Document.id
        ).filter(
            ExtractedDocument.id.in_(request.ids),
            Document.tenant_id == tenant_id
        ).all()
        
        found_ids = {record.id for record in records}
        missing_ids = set(request.ids) - found_ids
        if missing_ids:
            errors.append(f"Extracted document records not found: {', '.join(map(str, missing_ids))}")
        
        for record in records:
            try:
                record.approval_status = ApprovalStatus[request_status]
                record.approver_id = user.id
                record.modified_by = str(user.id)
                
                if request_status == "APPROVED":
                    record.approved_on = datetime.utcnow()
                else:
                    record.approved_on = None
                
                db.add(record)
                approved_count += 1
            except Exception as e:
                errors.append(f"Error updating record {record.id}: {str(e)}")
                logger.error(f"Error updating extracted document {record.id}: {e}", exc_info=True)
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            errors.append(f"Database error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to commit changes: {str(e)}"
            )
        
        status_verb = request_status.capitalize()
        message = f"{status_verb} {approved_count} extracted document(s)"
        
        return ExtractedDocumentBulkApproveResponse(
            status="success" if not errors else "partial_success",
            approved_count=approved_count,
            errors=errors,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk approving extracted documents: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk approve extracted documents: {str(e)}"
        )


@extraction_router.post("/files/bulk_delete", response_model=ExtractedDocumentBulkDeleteResponse)
async def bulk_delete_extracted_documents(
    request: ExtractedDocumentBulkDeleteRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Bulk delete extracted documents.
    
    Accepts a list of extracted document IDs and permanently deletes them.
    Only deletes documents that belong to the authenticated user's tenant.
    """
    try:
        user = ensure_user_exists(db, draup_user)
        tenant_id = str(draup_user.data.get("company_id", ""))
        
        if not request.ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No IDs provided"
            )
        
        errors = []
        deleted_count = 0
        
        records = db.query(ExtractedDocument).join(
            Document,
            ExtractedDocument.document_id == Document.id
        ).filter(
            ExtractedDocument.id.in_(request.ids),
            Document.tenant_id == tenant_id
        ).all()
        
        found_ids = {record.id for record in records}
        missing_ids = set(request.ids) - found_ids
        if missing_ids:
            errors.append(f"Extracted document records not found: {', '.join(map(str, missing_ids))}")
        
        for record in records:
            try:
                db.delete(record)
                deleted_count += 1
            except Exception as e:
                errors.append(f"Error deleting record {record.id}: {str(e)}")
                logger.error(f"Error deleting extracted document {record.id}: {e}", exc_info=True)
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            errors.append(f"Database error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to commit changes: {str(e)}"
            )
        
        message = f"Deleted {deleted_count} extracted document(s)"
        
        return ExtractedDocumentBulkDeleteResponse(
            status="success" if not errors else "partial_success",
            deleted_count=deleted_count,
            errors=errors,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk deleting extracted documents: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk delete extracted documents: {str(e)}"
        )


@extraction_router.get("/document/{document_id}/data", response_model=Union[DocumentDataResponse, RoleTaxonomyListResponse])
async def get_document_data(
    document_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Get extraction data for a specific document.

    Returns the extracted tasks, skills, stages, and other data
    for the specified document ID.
    If document_type is "role_taxonomy", returns role taxonomy data instead.
    """
    try:
        user = ensure_user_exists(db, draup_user)
        tenant_id = str(draup_user.data.get("company_id", ""))
        
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == tenant_id
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied"
            )

        extraction = db.query(ExtractedDocument).filter(
            ExtractedDocument.document_id == document_id,
            ExtractedDocument.status == ExtractionStatus.COMPLETED
        ).first()
        
        if not extraction:
            extraction = db.query(ExtractedDocument).filter(
                ExtractedDocument.document_id == document_id
            ).order_by(ExtractedDocument.created_on.desc()).first()

        if not extraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No extraction data found for this document"
            )

        if extraction.document_type and extraction.document_type.lower() == "role_taxonomy":
            base_query = db.query(RoleTaxonomy).filter(
                RoleTaxonomy.company_id == user.company_id
            ).order_by(RoleTaxonomy.created_on.desc())
            
            pending_count = db.query(RoleTaxonomy).filter(
                RoleTaxonomy.company_id == user.company_id,
                RoleTaxonomy.approval_status == "pending"
            ).count()
            
            paginated_result = paginate(base_query, page=page, page_size=page_size)
            role_taxonomy_records = paginated_result.items
            
            master_names = get_master_table_names(db, role_taxonomy_records)
            
            user_ids = set()
            for record in role_taxonomy_records:
                if record.user_id:
                    user_ids.add(record.user_id)
                if record.approver_id:
                    user_ids.add(record.approver_id)
            
            users_dict = {}
            if user_ids:
                users = db.query(User).filter(User.id.in_(user_ids)).all()
                users_dict = {user.id: user.username for user in users}
            
            role_taxonomy_data = []
            for record in role_taxonomy_records:
                occupation_name = record.occupation
                if record.occupation_id and record.occupation_id in master_names['occupation']:
                    occupation_name = master_names['occupation'][record.occupation_id]
                
                job_family_name = record.job_family
                if record.job_family_id and record.job_family_id in master_names['job_family']:
                    job_family_name = master_names['job_family'][record.job_family_id]
                
                job_track_name = record.job_track
                if record.job_track_id and record.job_track_id in master_names['job_track']:
                    job_track_name = master_names['job_track'][record.job_track_id]
                
                management_level_name = record.management_level
                if record.management_level_id and record.management_level_id in master_names['management_level']:
                    management_level_name = master_names['management_level'][record.management_level_id]
                
                role_taxonomy_data.append(RoleTaxonomyResponse(
                    id=record.id,
                    company_id=record.company_id,
                    job_id=record.job_id,
                    job_role=record.job_role,
                    job_title=record.job_title,
                    occupation=occupation_name,
                    job_family=job_family_name,
                    job_level=record.job_level,
                    job_track=job_track_name,
                    management_level=management_level_name,
                    pay_grade=record.pay_grade,
                    draup_role=record.draup_role,
                    job_description=record.job_description,
                    general_summary=record.general_summary,
                    duties_responsibilities=record.duties_responsibilities,
                    work_experience=record.work_experience,
                    skills=record.skills,
                    others=record.others,
                    source=record.source,
                    status=record.status,
                    approver_username=users_dict.get(record.approver_id) if record.approver_id else None,
                    user_username=users_dict.get(record.user_id) if record.user_id else None,
                    modified_by_username=record.modified_by,
                    created_on=record.created_on,
                    updated_on=record.modified_on
                ))
            
            return RoleTaxonomyListResponse(
                data=role_taxonomy_data,
                total_count=paginated_result.total,
                pending_count=pending_count,
                page=paginated_result.page,
                page_size=paginated_result.page_size,
                total_pages=paginated_result.total_pages,
                has_next=paginated_result.has_next,
                has_prev=paginated_result.has_prev
            )

        return DocumentDataResponse(
            document_id=str(extraction.document_id),
            document_name=extraction.document_name or document.original_filename,
            status=extraction.status.value,
            document_type=extraction.document_type,
            extraction_confidence=extraction.extraction_confidence,
            tasks=extraction.tasks,
            skills=extraction.skills,
            stages=extraction.stages,
            task_to_skill=extraction.task_to_skill,
            roles=extraction.roles,
            approval_status=extraction.approval_status.value,
            created_on=extraction.created_on,
            modified_on=extraction.modified_on
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document data {document_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document data: {str(e)}"
        )


@extraction_router.put("/document/{document_id}/update", response_model=DocumentDataResponse)
async def update_document_data(
    document_id: UUID,
    request: UpdateDocumentDataRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Update extraction data for a specific document.

    Updates the extracted tasks, skills, stages, roles, and other data
    for the specified document ID. Only updates fields that are provided
    in the request (partial update).
    """
    try:
        user = ensure_user_exists(db, draup_user)
        tenant_id = str(draup_user.data.get("company_id", ""))
        
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == tenant_id
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied"
            )

        extraction = db.query(ExtractedDocument).filter(
            ExtractedDocument.document_id == document_id,
            ExtractedDocument.status == ExtractionStatus.COMPLETED
        ).first()
        
        if not extraction:
            extraction = db.query(ExtractedDocument).filter(
                ExtractedDocument.document_id == document_id
            ).order_by(ExtractedDocument.created_on.desc()).first()

        if not extraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No extraction data found for this document"
            )

        document_name = getattr(request, 'document_name', None)
        if document_name is not None:
            extraction.document_name = document_name
        
        document_type = getattr(request, 'document_type', None)
        if document_type is not None:
            extraction.document_type = document_type
        
        extraction_confidence = getattr(request, 'extraction_confidence', None)
        if extraction_confidence is not None:
            extraction.extraction_confidence = extraction_confidence
        
        tasks = getattr(request, 'tasks', None)
        if tasks is not None:
            extraction.tasks = tasks
        
        skills = getattr(request, 'skills', None)
        if skills is not None:
            extraction.skills = skills
        
        stages = getattr(request, 'stages', None)
        if stages is not None:
            extraction.stages = stages
        
        task_to_skill = getattr(request, 'task_to_skill', None)
        if task_to_skill is not None:
            extraction.task_to_skill = task_to_skill
        
        roles = getattr(request, 'roles', None)
        if roles is not None:
            extraction.roles = roles
        
        approval_status = getattr(request, 'approval_status', None)
        if approval_status is not None:
            extraction.approval_status = approval_status
            extraction.approver_id = user.id

        extraction.modified_by = str(user.id)

        db.commit()
        db.refresh(extraction)

        logger.info(
            f"Updated extraction data for document {document_id} by user {user.id}"
        )

        return DocumentDataResponse(
            document_id=str(extraction.document_id),
            document_name=extraction.document_name or document.original_filename,
            status=extraction.status.value,
            document_type=extraction.document_type,
            extraction_confidence=extraction.extraction_confidence,
            tasks=extraction.tasks,
            skills=extraction.skills,
            stages=extraction.stages,
            task_to_skill=extraction.task_to_skill,
            roles=extraction.roles,
            approval_status=extraction.approval_status.value,
            created_on=extraction.created_on,
            modified_on=extraction.modified_on
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating document data {document_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document data: {str(e)}"
        )



@extraction_router.get("/role_taxonomy/company/{company_id}", response_model=RoleTaxonomyListResponse)
async def get_role_taxonomy_by_company(
    company_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(300, ge=1),
    status_filter: Optional[str] = Query(None, alias="status"),
    job_title: Optional[str] = Query(None),
    sort_column: Optional[str] = Query(None),
    sort_type: Optional[str] = Query(None),
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Get role taxonomy records for a specific company with pagination and filtering.
    
    Returns all columns with username lookups for approver and user.
    Supports pagination, optional status filtering, optional job_title filtering, and optional sorting.
    Returns a flat array list of role taxonomy records.
    """
    try:
        ensure_user_exists(db, draup_user)
        result = get_taxonomy_by_company_generic(
            db, 'role', company_id, page, page_size, status_filter, job_title, sort_column, sort_type
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve role taxonomy data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving role taxonomy for company {company_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve role taxonomy data: {str(e)}"
        )


@extraction_router.post("/role_taxonomy/bulk_upsert", response_model=RoleTaxonomyBulkUpsertResponse)
async def bulk_upsert_role_taxonomy(
    request: RoleTaxonomyBulkUpsertRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Bulk upsert role taxonomy records.
    
    Handles FK relationships efficiently by fetching all required data upfront.
    If force_update is True, creates master table entries if they don't exist.
    """
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        if request.company_name:
            company = db.query(MasterCompany).filter(MasterCompany.company_name == request.company_name).first()
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Company with name '{request.company_name}' not found"
                )
            user_company_id = company.id
        else:
            user_company_id = current_user.company_id
        
        force_update_flag = request.force_update or request.force_upload
        
        result = bulk_upsert_taxonomy_generic(
            db, 'role', request.items, force_update_flag, current_user, user_company_id
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bulk upsert role taxonomy data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk upserting role taxonomy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk upsert role taxonomy data: {str(e)}"
        )


@extraction_router.post("/role_taxonomy/bulk_approve", response_model=RoleTaxonomyBulkApproveResponse)
async def bulk_approve_role_taxonomy(
    request: RoleTaxonomyBulkApproveRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Bulk update role taxonomy records by setting status.
    
    Accepts a list of role taxonomy IDs and updates their status to the provided value.
    Defaults to 'approved' if status is not provided.
    """
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        result = bulk_approve_taxonomy_generic(
            db, RoleTaxonomy, RoleTaxonomyBulkApproveResponse,
            current_user, request.ids, request.status, "role taxonomy"
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bulk approve role taxonomy data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk approving role taxonomy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk approve role taxonomy data: {str(e)}"
        )


@extraction_router.post("/role_taxonomy/bulk_delete", response_model=RoleTaxonomyBulkDeleteResponse)
async def bulk_delete_role_taxonomy(
    request: RoleTaxonomyBulkDeleteRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        result = bulk_delete_taxonomy_generic(
            db, RoleTaxonomy, RoleTaxonomyBulkDeleteResponse,
            current_user, request.ids, "role taxonomy"
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bulk delete role taxonomy data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk deleting role taxonomy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk delete role taxonomy data: {str(e)}"
        )


@extraction_router.delete("/role_taxonomy/{role_taxonomy_id}", response_model=RoleTaxonomyDeleteResponse)
async def delete_role_taxonomy(
    role_taxonomy_id: int,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        result = delete_taxonomy_generic(
            db, RoleTaxonomy, RoleTaxonomyDeleteResponse,
            current_user, role_taxonomy_id, "role taxonomy"
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete role taxonomy data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting role taxonomy {role_taxonomy_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete role taxonomy data: {str(e)}"
        )


@extraction_router.get("/skill_taxonomy/company/{company_id}", response_model=SkillTaxonomyListResponse)
async def get_skill_taxonomy_by_company(
    company_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(300, ge=1),
    status_filter: Optional[str] = Query(None, alias="status"),
    skill_name: Optional[str] = Query(None),
    job_titles: Optional[List[str]] = Query(None, description="Filter by job titles (case-insensitive contains)"),
    sort_column: Optional[str] = Query(None),
    sort_type: Optional[str] = Query(None),
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Get skill taxonomy records for a specific company with pagination and filtering.
    
    Returns all columns with username lookups for approver, user, and modified_by.
    Supports pagination, optional status filtering, optional skill_name filtering, and optional sorting.
    Returns a flat array list of skill taxonomy records.
    """
    try:
        ensure_user_exists(db, draup_user)
        result = get_taxonomy_by_company_generic(
            db, 'skill', company_id, page, page_size, status_filter, skill_name, sort_column, sort_type, job_titles
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve skill taxonomy data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving skill taxonomy for company {company_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve skill taxonomy data: {str(e)}"
        )


@extraction_router.post("/skill_taxonomy/bulk_upsert", response_model=SkillTaxonomyBulkUpsertResponse)
async def bulk_upsert_skill_taxonomy(
    request: SkillTaxonomyBulkUpsertRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Bulk upsert skill taxonomy records.
    
    Handles FK relationships efficiently by fetching all required data upfront.
    If force_update is True, creates master table entries if they don't exist.
    """
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        if request.company_name:
            company = db.query(MasterCompany).filter(MasterCompany.company_name == request.company_name).first()
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Company with name '{request.company_name}' not found"
                )
            user_company_id = company.id
        else:
            user_company_id = current_user.company_id
        
        force_update_flag = request.force_update or request.force_upload
        
        result = bulk_upsert_taxonomy_generic(
            db, 'skill', request.items, force_update_flag, current_user, user_company_id
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bulk upsert skill taxonomy data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk upserting skill taxonomy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk upsert skill taxonomy data: {str(e)}"
        )


@extraction_router.post("/skill_taxonomy/bulk_approve", response_model=SkillTaxonomyBulkApproveResponse)
async def bulk_approve_skill_taxonomy(
    request: SkillTaxonomyBulkApproveRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Bulk update skill taxonomy records by setting status.
    
    Accepts a list of skill taxonomy IDs and updates their status to the provided value.
    Defaults to 'approved' if status is not provided.
    """
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        result = bulk_approve_taxonomy_generic(
            db, SkillTaxonomy, SkillTaxonomyBulkApproveResponse,
            current_user, request.ids, request.status, "skill taxonomy"
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bulk approve skill taxonomy data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk approving skill taxonomy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk approve skill taxonomy data: {str(e)}"
        )


@extraction_router.post("/skill_taxonomy/bulk_delete", response_model=SkillTaxonomyBulkDeleteResponse)
async def bulk_delete_skill_taxonomy(
    request: SkillTaxonomyBulkDeleteRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        result = bulk_delete_taxonomy_generic(
            db, SkillTaxonomy, SkillTaxonomyBulkDeleteResponse,
            current_user, request.ids, "skill taxonomy"
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bulk delete skill taxonomy data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk deleting skill taxonomy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk delete skill taxonomy data: {str(e)}"
        )


@extraction_router.delete("/skill_taxonomy/{skill_taxonomy_id}", response_model=SkillTaxonomyDeleteResponse)
async def delete_skill_taxonomy(
    skill_taxonomy_id: int,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        result = delete_taxonomy_generic(
            db, SkillTaxonomy, SkillTaxonomyDeleteResponse,
            current_user, skill_taxonomy_id, "skill taxonomy"
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete skill taxonomy data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting skill taxonomy {skill_taxonomy_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete skill taxonomy data: {str(e)}"
        )


async def _fetch_and_transform_tech_stack_from_draup(
    db: Session,
    company_name: str,
    user_token: Optional[str] = None
) -> List[TechStackTaxonomyBulkUpsertItem]:
    """
    Helper function to fetch tech stack from Draup and transform into bulk upsert items.
    
    Args:
        db: Database session
        company_name: Company name to search in Draup
        user_token: Optional user token. If not provided, uses DRAUP_PLATFORM_TOKEN
        
    Returns:
        List of TechStackTaxonomyBulkUpsertItem
    """
    from services.draup_service import fetch_tech_stack_from_draup_api, get_company_id_by_name
    
    logger.info(f"Resolving company name '{company_name}' to Draup company ID...")
    draup_company_id = await get_company_id_by_name(company_name)
    
    if draup_company_id is None:
        logger.warning(f"Could not resolve company name '{company_name}' to Draup company ID")
        return []
    
    token = user_token or os.environ.get('DRAUP_PLATFORM_TOKEN')
    if not token:
        logger.warning("Token not configured, cannot fetch from Draup")
        return []
    
    draup_data = await fetch_tech_stack_from_draup_api(draup_company_id, token)
    tech_stack_products = draup_data.get('result', [])
    items = []
    
    for product in tech_stack_products:
        tech_stack_product_name = product.get('tech_stack_product', 'Unknown')
        
        tech_stack_id = None
        category_from_master = None
        description_from_master = None
        if tech_stack_product_name and tech_stack_product_name != 'Unknown':
            from sqlalchemy.orm import joinedload
            master_tech_stack = db.query(MasterTechStack).options(
                joinedload(MasterTechStack.g2_category)
            ).filter(
                MasterTechStack.product_name.ilike(tech_stack_product_name)
            ).first()
            if master_tech_stack:
                tech_stack_id = master_tech_stack.id
                description_from_master = master_tech_stack.description
                if master_tech_stack.g2_category:
                    g2_category_name = master_tech_stack.g2_category.g2_sub_sub_category_3
                    if g2_category_name:
                        category_from_master_record = db.query(MasterTechStackCategory).filter(
                            MasterTechStackCategory.name.ilike(g2_category_name.strip())
                        ).first()
                        if category_from_master_record:
                            category_from_master = category_from_master_record.name
                        else:
                            category_from_master = g2_category_name.strip()
        
        category_value = category_from_master or product.get('tech_stack_category')
        if category_value:
            category_value = category_value.strip()
        
        description_value = description_from_master or product.get('g2_sub_category_name')
        
        item = TechStackTaxonomyBulkUpsertItem(
            tech_stack_name=tech_stack_product_name,
            description=description_value,
            image_link=product.get('product_picture_url'),
            category=category_value if category_value else None,
            tech_stack_id=tech_stack_id,
            source="Etter",
            status="pending"
        )
        items.append(item)
    
    logger.info(f"Successfully transformed {len(items)} tech stack products from Draup for company '{company_name}'")
    return items


@extraction_router.get("/tech_stack_taxonomy/company/{company_id}", response_model=TechStackTaxonomyListResponse)
async def get_tech_stack_taxonomy_by_company(
    company_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(300, ge=1),
    status_filter: Optional[str] = Query(None, alias="status"),
    tech_stack_name: Optional[str] = Query(None),
    job_titles: Optional[List[str]] = Query(None, description="Filter by job titles (case-insensitive contains)"),
    sort_column: Optional[str] = Query(None),
    sort_type: Optional[str] = Query(None),
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Get tech stack taxonomy records for a specific company with pagination and filtering.
    
    Returns all columns with username lookups for approver, user, and modified_by.
    Supports pagination, optional status filtering, optional tech_stack_name filtering, and optional sorting.
    Returns a flat array list of tech stack taxonomy records.
    
    If no data is found, automatically fetches from Draup platform and retries.
    """
    try:
        ensure_user_exists(db, draup_user)
        result = get_taxonomy_by_company_generic(
            db, 'tech_stack', company_id, page, page_size, status_filter, tech_stack_name, sort_column, sort_type, job_titles
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve tech stack taxonomy data"
            )
        
        if result.total_count == 0 or not result.data:
            logger.info(f"No tech stack taxonomy data found for company {company_id}, fetching from Draup...")
            
            try:
                draup_user_data = draup_user.data
                current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
                if not current_user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User not found",
                    )
                
                company = db.query(MasterCompany).filter(MasterCompany.id == company_id).first()
                if not company:
                    logger.warning(f"Company with ID {company_id} not found in MasterCompany")
                else:
                    company_name = company.company_name
                    items = await _fetch_and_transform_tech_stack_from_draup(db, company_name)
                    
                    if items:
                        user_company_id = current_user.company_id
                        force_update_flag = True
                        
                        bulk_upsert_taxonomy_generic(
                            db, 'tech_stack', items, force_update_flag, current_user, user_company_id
                        )
                        
                        logger.info(f"Successfully fetched and saved {len(items)} tech stack products from Draup for company {company_id} (company_name: {company_name})")
                        
                        result = get_taxonomy_by_company_generic(
                            db, 'tech_stack', company_id, page, page_size, status_filter, tech_stack_name, sort_column, sort_type
                        )
                        if result is None:
                            raise HTTPException(
                                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Failed to retrieve tech stack taxonomy data after fetch"
                            )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error fetching tech stack from Draup for company {company_id}: {str(e)}", exc_info=True)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving tech stack taxonomy for company {company_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tech stack taxonomy data: {str(e)}"
        )


@extraction_router.post("/tech_stack_taxonomy/bulk_upsert", response_model=TechStackTaxonomyBulkUpsertResponse)
async def bulk_upsert_tech_stack_taxonomy(
    request: TechStackTaxonomyBulkUpsertRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Bulk upsert tech stack taxonomy records.
    
    Handles FK relationships efficiently by fetching all required data upfront.
    If force_update is True, creates master table entries if they don't exist.
    """
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        if request.company_name:
            company = db.query(MasterCompany).filter(MasterCompany.company_name == request.company_name).first()
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Company with name '{request.company_name}' not found"
                )
            user_company_id = company.id
        else:
            user_company_id = current_user.company_id
        
        force_update_flag = request.force_update or request.force_upload
        
        result = bulk_upsert_taxonomy_generic(
            db, 'tech_stack', request.items, force_update_flag, current_user, user_company_id
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bulk upsert tech stack taxonomy data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk upserting tech stack taxonomy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk upsert tech stack taxonomy data: {str(e)}"
        )


@extraction_router.post("/tech_stack_taxonomy/bulk_approve", response_model=TechStackTaxonomyBulkApproveResponse)
async def bulk_approve_tech_stack_taxonomy(
    request: TechStackTaxonomyBulkApproveRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Bulk update tech stack taxonomy records by setting status.
    
    Accepts a list of tech stack taxonomy IDs and updates their status to the provided value.
    Defaults to 'approved' if status is not provided.
    """
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        result = bulk_approve_taxonomy_generic(
            db, TechStackTaxonomy, TechStackTaxonomyBulkApproveResponse,
            current_user, request.ids, request.status, "tech stack taxonomy"
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bulk approve tech stack taxonomy data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk approving tech stack taxonomy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk approve tech stack taxonomy data: {str(e)}"
        )


@extraction_router.post("/tech_stack_taxonomy/bulk_delete", response_model=TechStackTaxonomyBulkDeleteResponse)
async def bulk_delete_tech_stack_taxonomy(
    request: TechStackTaxonomyBulkDeleteRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        result = bulk_delete_taxonomy_generic(
            db, TechStackTaxonomy, TechStackTaxonomyBulkDeleteResponse,
            current_user, request.ids, "tech stack taxonomy"
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bulk delete tech stack taxonomy data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk deleting tech stack taxonomy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk delete tech stack taxonomy data: {str(e)}"
        )


@extraction_router.delete("/tech_stack_taxonomy/{tech_stack_taxonomy_id}", response_model=TechStackTaxonomyDeleteResponse)
async def delete_tech_stack_taxonomy(
    tech_stack_taxonomy_id: int,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    try:
        draup_user_data = draup_user.data
        current_user = db.query(User).filter(User.email == draup_user_data["email"]).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        result = delete_taxonomy_generic(
            db, TechStackTaxonomy, TechStackTaxonomyDeleteResponse,
            current_user, tech_stack_taxonomy_id, "tech stack taxonomy"
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete tech stack taxonomy data"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tech stack taxonomy {tech_stack_taxonomy_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tech stack taxonomy data: {str(e)}"
        )


@extraction_router.post("/tech_stack_taxonomy/fetch_from_draup")
async def fetch_tech_stack_from_draup(
    company_id: Optional[int] = Query(None, description="Draup company ID"),
    company_name: Optional[str] = Query(None, min_length=1, max_length=200, description="Company name to search"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Fetch tech stack products from Draup platform API and transform into bulk upsert format.
    
    Provide either company_id OR company_name (not both):
    - company_id: Direct Draup company/account ID
    - company_name: Company name to search (e.g., "NVIDIA", "Goldman Sachs")
    
    Uses the authenticated user's token for Draup API calls.
    
    First checks if tech stack data exists in database. Only fetches from Draup if count is zero.
    """
    try:
        ensure_user_exists(db, draup_user)
        
        # Extract token from request credentials
        user_token = credentials.credentials
        
        # Validate: require exactly one parameter
        if company_id is None and company_name is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either company_id or company_name must be provided"
            )
        
        if company_id is not None and company_name is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide either company_id OR company_name, not both"
            )
        
        master_company_id = None
        resolved_company_name = None
        
        if company_name is not None:
            company_name = company_name.strip()
            if not company_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Company name cannot be empty"
                )
            company = db.query(MasterCompany).filter(
                MasterCompany.company_name.ilike(company_name)
            ).first()
            if company:
                master_company_id = company.id
                resolved_company_name = company.company_name
            else:
                resolved_company_name = company_name
        else:
            from services.draup_service import get_company_id_by_name
            
            draup_company_id = company_id
            draup_company_name = None
            
            company = db.query(MasterCompany).filter(MasterCompany.id == company_id).first()
            if company:
                master_company_id = company.id
                resolved_company_name = company.company_name
            else:
                logger.warning(f"Company ID {company_id} not found in MasterCompany, treating as Draup company ID")
        
        if master_company_id:
            tech_stack_count = db.query(TechStackTaxonomy).filter(
                TechStackTaxonomy.company_id == master_company_id
            ).count()
            
            if tech_stack_count > 0:
                logger.info(f"Found {tech_stack_count} tech stack records in database for company {master_company_id}, fetching from DB")
                
                tech_stack_records = db.query(TechStackTaxonomy).filter(
                    TechStackTaxonomy.company_id == master_company_id
                ).all()
                
                category_ids = {r.category_id for r in tech_stack_records if r.category_id}
                category_names = {}
                if category_ids:
                    categories = db.query(MasterTechStackCategory).filter(
                        MasterTechStackCategory.id.in_(category_ids)
                    ).all()
                    category_names = {cat.id: cat.name for cat in categories}
                
                items = []
                for record in tech_stack_records:
                    category_name = category_names.get(record.category_id) if record.category_id else None
                    
                    item = TechStackTaxonomyBulkUpsertItem(
                        tech_stack_name=record.tech_stack_name,
                        description=record.description,
                        image_link=record.image_link,
                        category=category_name,
                        tech_stack_id=record.tech_stack_id,
                        source=record.source,
                        status=record.status
                    )
                    items.append(item)
                
                return TechStackTaxonomyBulkUpsertRequest(
                    items=items,
                    force_update=False,
                    force_upload=False
                )
        
        logger.info(f"No tech stack data found in database, fetching from Draup...")
        
        if resolved_company_name:
            items = await _fetch_and_transform_tech_stack_from_draup(db, resolved_company_name, user_token)
        else:
            from services.draup_service import fetch_tech_stack_from_draup_api
            
            draup_data = await fetch_tech_stack_from_draup_api(company_id, user_token)
            
            tech_stack_products = draup_data.get('result', [])
            items = []
            
            for product in tech_stack_products:
                tech_stack_product_name = product.get('tech_stack_product', 'Unknown')
                
                tech_stack_id = None
                category_from_master = None
                description_from_master = None
                if tech_stack_product_name and tech_stack_product_name != 'Unknown':
                    from sqlalchemy.orm import joinedload
                    master_tech_stack = db.query(MasterTechStack).options(
                        joinedload(MasterTechStack.g2_category)
                    ).filter(
                        MasterTechStack.product_name.ilike(tech_stack_product_name)
                    ).first()
                    if master_tech_stack:
                        tech_stack_id = master_tech_stack.id
                        description_from_master = master_tech_stack.description
                        if master_tech_stack.g2_category:
                            g2_category_name = master_tech_stack.g2_category.g2_sub_sub_category_3
                            if g2_category_name:
                                category_from_master_record = db.query(MasterTechStackCategory).filter(
                                    MasterTechStackCategory.name.ilike(g2_category_name.strip())
                                ).first()
                                if category_from_master_record:
                                    category_from_master = category_from_master_record.name
                                else:
                                    category_from_master = g2_category_name.strip()
                
                category_value = category_from_master or product.get('tech_stack_category')
                if category_value:
                    category_value = category_value.strip()
                
                description_value = description_from_master or product.get('g2_sub_category_name')
                
                item = TechStackTaxonomyBulkUpsertItem(
                    tech_stack_name=tech_stack_product_name,
                    description=description_value,
                    image_link=product.get('product_picture_url'),
                    category=category_value if category_value else None,
                    tech_stack_id=tech_stack_id,
                    source="Etter",
                    status="pending"
                )
                items.append(item)
            
            logger.info(f"Successfully transformed {len(items)} tech stack products from Draup for company {company_id}")
        
        if not items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No tech stack products found or could not fetch from Draup"
            )
        
        return TechStackTaxonomyBulkUpsertRequest(
            items=items,
            force_update=False,
            force_upload=False
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing tech stack from Draup for company {company_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process tech stack products: {str(e)}"
        )



# ==================== Background Task ====================

def _run_extraction(extracted_doc_id: int, tenant_id: str):
    """
    Background task to run extraction.

    Note: This creates a new DB session since background tasks
    run outside the request context.
    """
    from settings.database import SessionLocal

    db = SessionLocal()
    try:
        extracted_doc = db.query(ExtractedDocument).get(extracted_doc_id)
        if not extracted_doc:
            logger.error(f"ExtractedDocument {extracted_doc_id} not found")
            return

        # Create service and process
        from api.s3.infra.db.uow import UnitOfWork
        from api.s3.infra.s3.s3_management_service import S3ManagementService

        uow = UnitOfWork(db)
        s3_service = S3ManagementService()
        service = ExtractionService(uow, s3_service)

        service.process_document(extracted_doc, tenant_id, db)

        # Session status no longer auto-updated - manual completion required via /complete endpoint
        logger.info(
            f"Document {extracted_doc_id} processing complete. "
            f"Session {extracted_doc.session_id} requires manual completion via /complete endpoint."
        )

    except Exception as e:
        logger.error(f"Background extraction failed: {e}", exc_info=True)
    finally:
        db.close()


def _run_batch_extraction(extracted_doc_ids: List[int], tenant_id: str):
    """
    Background task for sequential batch extraction.

    Processes multiple documents one at a time to avoid overloading
    the Draup World Model API. Continues processing even if individual
    documents fail.
    """
    from settings.database import SessionLocal

    db = SessionLocal()
    session_id = None

    try:
        logger.info(f"Starting batch extraction for {len(extracted_doc_ids)} documents")

        from api.s3.infra.db.uow import UnitOfWork
        from api.s3.infra.s3.s3_management_service import S3ManagementService

        uow = UnitOfWork(db)
        s3_service = S3ManagementService()
        service = ExtractionService(uow, s3_service)

        # Process each document sequentially
        for idx, doc_id in enumerate(extracted_doc_ids, 1):
            try:
                logger.info(f"Processing document {idx}/{len(extracted_doc_ids)}: record_id={doc_id}")

                extracted_doc = db.query(ExtractedDocument).get(doc_id)
                if not extracted_doc:
                    logger.error(f"ExtractedDocument {doc_id} not found")
                    continue

                if session_id is None:
                    session_id = extracted_doc.session_id

                # Process the document
                service.process_document(extracted_doc, tenant_id, db)

                logger.info(f"Completed document {idx}/{len(extracted_doc_ids)}: status={extracted_doc.status.value}")

            except Exception as e:
                logger.error(f"Failed to process document {doc_id}: {e}", exc_info=True)
                continue

        # Session status no longer auto-updated - manual completion required via /complete endpoint
        if session_id:
            logger.info(
                f"Batch extraction completed for {len(extracted_doc_ids)} documents. "
                f"Session {session_id} requires manual completion via /complete endpoint."
            )

    except Exception as e:
        logger.error(f"Batch extraction failed: {e}", exc_info=True)
    finally:
        db.close()


# =============================================================================
# Taxonomy Extraction API (LLM-based schema mapping)
# =============================================================================

@extraction_router.post(
    "/taxonomy/extract",
    response_model=TaxonomyExtractionResponse,
    summary="Extract taxonomy data from document using LLM",
    description="""
    Use LLM to infer column mappings from an uploaded Excel/CSV document 
    to taxonomy fields (role, skill, or tech_stack).
    
    **Workflow:**
    1. Provide document_id of an uploaded Excel/CSV file
    2. Server downloads file and parses columns/rows
    3. LLM infers column->field mappings
    4. Data is validated and transformed
    5. If preview_only=false, data is upserted
    
    **Conflict Resolution:**
    - Duplicates within document are detected and first occurrence kept
    - Conflicts with existing DB records are reported
    """
)
async def extract_taxonomy(
    request: TaxonomyExtractionRequest,
    draup_user: ResponseModel = Depends(verify_token),
    db: Session = Depends(get_db),
    uow: UnitOfWork = Depends(get_uow),
    s3_service: S3ManagementService = Depends(get_s3_service)
):
    """Extract taxonomy data from document using LLM-based column mapping."""
    import time
    import requests
    from api.etter_apis import get_draup_world_api, get_token
    
    start_time = time.time()
    
    try:
        # Verify user from token
        if draup_user.status != "Success" or not draup_user.data:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Get tenant_id and user info directly from token data
        user_data = draup_user.data
        tenant_id = str(user_data.get("company_id")) if user_data.get("company_id") else "default"
        user_id = user_data.get("user_id")
        username = user_data.get("email", "unknown")
        
        logger.info(
            f"Taxonomy extraction request: document_id={request.document_id}, "
            f"type={request.taxonomy_type}, user={username}"
        )
        
        # Generate presigned URL for the document
        try:
            service = ExtractionService(uow, s3_service)
            presigned_url, original_filename = service.get_presigned_url(
                document_id=request.document_id,
                tenant_id=tenant_id
            )
            logger.info(f"Generated presigned URL for document: {original_filename}")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to get presigned URL: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to access document: {str(e)}"
            )
        
        # Get token for draup_world API
        token = get_token()
        if not token:
            raise HTTPException(
                status_code=503,
                detail="Failed to obtain authentication token for extraction service"
            )
        
        # Fetch existing keys from database for conflict detection if company_id provided
        existing_keys = None
        if request.company_id:
            existing_keys = _get_existing_taxonomy_keys(
                db, 
                request.taxonomy_type.value, 
                request.company_id
            )
        
        # Prepare request for draup_world workflow
        target_url = f"{get_draup_world_api()}/workflows"
        headers = {
            # "Authorization": f"Token {token}",
            "Origin": "https://draup-world.draup.technology",
            "Content-Type": "application/json"
        }
        
        payload = {
            "workflow": "taxonomy_extraction",
            "step": "extract_taxonomy_mapping",
            "data": {
                "presigned_url": presigned_url,
                "document_name": original_filename,
                "taxonomy_type": request.taxonomy_type.value,
                "user_mapping": request.user_mapping,
                "sheet_name": request.sheet_name,
                "existing_keys": existing_keys
            }
        }
        
        # Call draup_world workflow
        response = requests.post(
            target_url, 
            headers=headers, 
            json=payload, 
            timeout=180  # Generous timeout for file download + LLM
        )
        
        if response.status_code != 200:
            logger.error(f"Taxonomy extraction failed: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Extraction service error: {response.text}"
            )
        
        result = response.json()
        
        # Extract step data
        step_data = result.get("current_step", {}).get("data", {})
        
        # Check for errors from the workflow
        if step_data.get("status") == "error":
            return TaxonomyExtractionResponse(
                status="error",
                taxonomy_type=request.taxonomy_type.value,
                mapping=ColumnMappingResult(),
                error=step_data.get("error"),
                execution_time=time.time() - start_time
            )
        
        # Build mapping result
        mapping_data = step_data.get("mapping", {})
        mapping = ColumnMappingResult(
            column_mappings=mapping_data.get("column_mappings", {}),
            unmapped_columns=mapping_data.get("unmapped_columns", []),
            required_fields_missing=mapping_data.get("required_fields_missing", []),
            confidence=mapping_data.get("confidence", 0.0),
            warnings=mapping_data.get("warnings", [])
        )
        
        # Build validation result if present
        validation = None
        validation_data = step_data.get("validation")
        if validation_data:
            validation = ValidationResult(
                total_rows=validation_data.get("total_rows", 0),
                valid_rows=validation_data.get("valid_rows", 0),
                duplicates_in_document=[
                    DuplicateRecord(**d) for d in validation_data.get("duplicates_in_document", [])
                ],
                conflicts_with_database=[
                    ConflictRecord(**c) for c in validation_data.get("conflicts_with_database", [])
                ],
                validation_errors=[
                    ValidationError(**e) for e in validation_data.get("validation_errors", [])
                ],
                warnings=validation_data.get("warnings", [])
            )
        
        # Get transformed data if available
        transformed_data = step_data.get("transformed_data")
        
        # Perform upsert if not preview_only and we have transformed data
        upsert_result = None
        if not request.preview_only and transformed_data and request.company_id:
            try:
                upsert_result = _perform_taxonomy_upsert(
                    db=db,
                    taxonomy_type=request.taxonomy_type.value,
                    records=transformed_data,
                    company_id=request.company_id,
                    user_id=user_id
                )
            except Exception as e:
                logger.error(f"Taxonomy upsert failed: {e}")
                upsert_result = {"status": "error", "error": str(e)}
        
        execution_time = time.time() - start_time
        
        return TaxonomyExtractionResponse(
            status="success",
            taxonomy_type=request.taxonomy_type.value,
            mapping=mapping,
            validation=validation,
            transformed_data=transformed_data if request.preview_only else None,
            upsert_result=upsert_result,
            execution_time=execution_time
        )
        
    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        logger.error("Taxonomy extraction timed out")
        raise HTTPException(
            status_code=504,
            detail="Extraction service timed out"
        )
    except Exception as e:
        logger.error(f"Taxonomy extraction error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


def _get_existing_taxonomy_keys(
    db: Session, 
    taxonomy_type: str, 
    company_id: int
) -> List[Dict]:
    """Fetch existing taxonomy keys for conflict detection."""
    try:
        if taxonomy_type == "role":
            records = db.query(
                RoleTaxonomy.id,
                RoleTaxonomy.job_title,
                RoleTaxonomy.job_family,
                RoleTaxonomy.occupation
            ).filter(
                RoleTaxonomy.company_id == company_id
            ).all()
            
            return [
                {"id": r.id, "job_title": r.job_title, "job_family": r.job_family, "occupation": r.occupation}
                for r in records
            ]
            
        elif taxonomy_type == "skill":
            records = db.query(
                SkillTaxonomy.id,
                SkillTaxonomy.skill_name
            ).filter(
                SkillTaxonomy.company_id == company_id
            ).all()
            
            return [
                {"id": r.id, "skill_name": r.skill_name}
                for r in records
            ]
            
        elif taxonomy_type == "tech_stack":
            records = db.query(
                TechStackTaxonomy.id,
                TechStackTaxonomy.tech_stack_name
            ).filter(
                TechStackTaxonomy.company_id == company_id
            ).all()
            
            return [
                {"id": r.id, "tech_stack_name": r.tech_stack_name}
                for r in records
            ]
            
        return []
        
    except Exception as e:
        logger.error(f"Error fetching existing taxonomy keys: {e}")
        return []


def _perform_taxonomy_upsert(
    db: Session,
    taxonomy_type: str,
    records: List[Dict],
    company_id: int,
    user_id: int
) -> Dict:
    """Perform bulk upsert of taxonomy records."""
    try:
        # Use existing bulk_upsert_taxonomy_generic function
        config = TAXONOMY_CONFIGS.get(taxonomy_type)
        if not config:
            return {"status": "error", "error": f"Unknown taxonomy type: {taxonomy_type}"}
        
        # Add company_id and user_id to each record
        for record in records:
            record["company_id"] = company_id
            record["user_id"] = user_id
            record["source"] = "LLM_Extraction"
        
        # Call the generic upsert
        result = bulk_upsert_taxonomy_generic(
            db=db,
            model=config.model,
            items_data=records,
            unique_fields=config.unique_fields,
            response_schema=config.response_schema,
            force_update=False,
            company_id=company_id,
            user_id=user_id,
            force_upload=False
        )
        
        return {
            "status": "success",
            "created_count": result.get("created_count", 0),
            "updated_count": result.get("updated_count", 0),
            "total_count": result.get("total_count", 0),
            "errors": result.get("errors", [])
        }
        
    except Exception as e:
        logger.error(f"Taxonomy upsert error: {e}")
        return {"status": "error", "error": str(e)}
