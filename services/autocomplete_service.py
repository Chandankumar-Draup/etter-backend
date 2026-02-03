from sqlalchemy.orm import Session
from sqlalchemy import text, func, or_
from typing import List, Dict, Any, Optional

from models.extraction import (
    RoleTaxonomy,
    SkillTaxonomy,
    MasterSkillTaxonomyCategories,
    TechStackTaxonomy,
    MasterTechStackCategory,
)
from models.etter import (
    MasterCompanyRoleManagementLevel,
    MasterCompanyRoleJobTrack,
    MasterCompanyRoleJobFamily,
    MasterCompanyRoleOccupation,
    FunctionWorkflow,
    SampleData,
)

DEFAULT_LIMIT = 10

DIRECT = "direct"
MASTER_JOIN = "master_join"
RAW = "raw"

AUTOCOMPLETE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "job_title": {
        "style": DIRECT,
        "model": RoleTaxonomy,
        "column": "job_title",
        "company_filter_column": "company_id",
        "default_limit": DEFAULT_LIMIT,
    },
    "management_level": {
        "style": MASTER_JOIN,
        "model": MasterCompanyRoleManagementLevel,
        "column": "name",
        "join_model": RoleTaxonomy,
        "join_fk_attr": "management_level_id",
        "company_filter_attr": "company_id",
        "default_limit": DEFAULT_LIMIT,
    },
    "job_track": {
        "style": MASTER_JOIN,
        "model": MasterCompanyRoleJobTrack,
        "column": "name",
        "join_model": RoleTaxonomy,
        "join_fk_attr": "job_track_id",
        "company_filter_attr": "company_id",
        "default_limit": DEFAULT_LIMIT,
    },
    "job_family": {
        "style": MASTER_JOIN,
        "model": MasterCompanyRoleJobFamily,
        "column": "name",
        "join_model": RoleTaxonomy,
        "join_fk_attr": "job_family_id",
        "company_filter_attr": "company_id",
        "default_limit": DEFAULT_LIMIT,
    },
    "occupation": {
        "style": MASTER_JOIN,
        "model": MasterCompanyRoleOccupation,
        "column": "name",
        "join_model": RoleTaxonomy,
        "join_fk_attr": "occupation_id",
        "company_filter_attr": "company_id",
        "default_limit": DEFAULT_LIMIT,
    },
    "skill_category": {
        "style": MASTER_JOIN,
        "model": MasterSkillTaxonomyCategories,
        "column": "name",
        "join_model": SkillTaxonomy,
        "join_fk_attr": "category_id",
        "company_filter_attr": "company_id",
        "default_limit": DEFAULT_LIMIT,
    },
    "tech_stack_category": {
        "style": MASTER_JOIN,
        "model": MasterTechStackCategory,
        "column": "name",
        "join_model": TechStackTaxonomy,
        "join_fk_attr": "category_id",
        "company_filter_attr": "company_id",
        "default_limit": DEFAULT_LIMIT,
    },
    "workflow": {
        "style": DIRECT,
        "model": FunctionWorkflow,
        "column": "workflow_name",
        "company_filter_column": None,
        "default_limit": DEFAULT_LIMIT,
        "response_key": "workflow_name",
    },
    "job_role": {
        "style": RAW,
        "table": "ace.machine_learning_jobrole",
        "column": "job_role",
        "default_limit": DEFAULT_LIMIT,
    },
    "company": {
        "style": RAW,
        "table": "iris1.iris1_mastercompany",
        "column": "company_name",
        "default_limit": DEFAULT_LIMIT,
    },
}


def _run_direct(
    db: Session,
    config: Dict[str, Any],
    search_string: Optional[str],
    company_id: Optional[int],
    limit: int,
) -> List[Any]:
    model = config["model"]
    col_name = config["column"]
    company_col = config.get("company_filter_column")
    response_key = config.get("response_key")
    col = getattr(model, col_name)
    subq = db.query(col.label("val"), func.length(col).label("_len"))
    if getattr(model, "job_title", None) is not None and col_name == "job_title":
        subq = subq.filter(col.isnot(None))
    if company_id and company_col:
        subq = subq.filter(getattr(model, company_col) == company_id)
    if search_string:
        subq = subq.filter(col.ilike(f"%{search_string}%"))
    subq = subq.distinct().subquery()
    results = (
        db.query(subq.c.val).order_by(subq.c._len).limit(limit).all()
    )
    values = [row[0] for row in results]
    if response_key:
        return [{response_key: v} for v in values]
    return values


def _run_master_join(
    db: Session,
    config: Dict[str, Any],
    search_string: Optional[str],
    company_id: Optional[int],
    limit: int,
) -> List[Any]:
    model = config["model"]
    col_name = config["column"]
    join_model = config["join_model"]
    join_fk_attr = config["join_fk_attr"]
    company_attr = config["company_filter_attr"]
    col = getattr(model, col_name)
    subquery = db.query(col).distinct()
    if company_id:
        subquery = subquery.join(
            join_model,
            getattr(join_model, join_fk_attr) == model.id,
        ).filter(getattr(join_model, company_attr) == company_id)
    if search_string:
        subquery = subquery.filter(col.ilike(f"%{search_string}%"))
    query = (
        db.query(col)
        .filter(col.in_(subquery))
        .order_by(func.length(col))
        .limit(limit)
    )
    results = query.all()
    return [row[0] for row in results]


def _run_raw(
    db: Session,
    config: Dict[str, Any],
    search_string: Optional[str],
    limit: int,
) -> List[Any]:
    table_name = config["table"]
    column_name = config["column"]
    if search_string:
        q = f"""
        SELECT {column_name}
        FROM {table_name}
        WHERE {column_name} ILIKE :search_value
        ORDER BY LENGTH({column_name}) ASC
        LIMIT :limit
        """
        result = db.execute(
            text(q),
            {"search_value": f"%{search_string}%", "limit": limit},
        )
    else:
        q = f"""
        SELECT {column_name}
        FROM {table_name}
        ORDER BY LENGTH({column_name}) ASC
        LIMIT :limit
        """
        result = db.execute(text(q), {"limit": limit})
    return [dict(row._mapping) for row in result]


def _sample_data_roles(
    db: Session,
    title: str,
    company_id: Optional[int],
    search_string: Optional[str],
    limit: int,
) -> List[str]:
    query = db.query(SampleData.role).filter(SampleData.title == title)
    if company_id is not None:
        query = query.filter(
            or_(
                SampleData.company_id == company_id,
                SampleData.is_global == True,
            )
        )
    else:
        query = query.filter(SampleData.is_global == True)
    if search_string:
        query = query.filter(SampleData.role.ilike(f"%{search_string}%"))
    results = query.distinct().limit(limit).all()
    return [row[0] for row in results]


def _high_level_func(
    db: Session,
    search_string: Optional[str],
    sub_level_func: Optional[str],
    limit: int,
) -> List[Dict[str, Any]]:
    conditions = []
    params = {"limit": limit}
    if sub_level_func:
        conditions.append("sub_level_func = :sub_level_func")
        params["sub_level_func"] = sub_level_func
    if search_string:
        conditions.append("high_level_func ILIKE :search_value")
        params["search_value"] = f"%{search_string}%"
    where_clause = " AND ".join(conditions) if conditions else ""
    q = f"""
    SELECT high_level_func
    FROM (
        SELECT DISTINCT high_level_func, LENGTH(high_level_func) as len_val
        FROM etter.etter_masterfunction
        {("WHERE " + where_clause) if where_clause else ""}
    ) AS distinct_values
    ORDER BY len_val ASC
    LIMIT :limit
    """
    result = db.execute(text(q), params)
    return [{"high_level_func": row[0]} for row in result]


def _sub_level_func(
    db: Session,
    search_string: Optional[str],
    high_level_func: Optional[str],
    limit: int,
) -> List[Dict[str, Any]]:
    conditions = []
    params = {"limit": limit}
    if high_level_func:
        conditions.append("high_level_func = :high_level_func")
        params["high_level_func"] = high_level_func
    if search_string:
        conditions.append("sub_level_func ILIKE :search_value")
        params["search_value"] = f"%{search_string}%"
    where_clause = " AND ".join(conditions) if conditions else ""
    q = f"""
    SELECT sub_level_func
    FROM (
        SELECT DISTINCT sub_level_func, LENGTH(sub_level_func) as len_val
        FROM etter.etter_masterfunction
        {("WHERE " + where_clause) if where_clause else ""}
    ) AS distinct_values
    ORDER BY len_val ASC
    LIMIT :limit
    """
    result = db.execute(text(q), params)
    return [{"sub_level_func": row[0]} for row in result]


def fetch_autocomplete_data(
    db: Session,
    search_type: str,
    search_string: Optional[str] = None,
    limit: int = 10,
    title: Optional[str] = None,
    company_id: Optional[int] = None,
    company: Optional[str] = None,
    role: Optional[str] = None,
    high_level_func: Optional[str] = None,
    sub_level_func: Optional[str] = None,
) -> List[Any]:
    if search_type == "task":
        from services.task_autocomplete_service import fetch_tasks_autocomplete

        if not company or not role:
            raise ValueError("company and role are required for task autocomplete")
        return fetch_tasks_autocomplete(
            db=db,
            company=company,
            role=role,
            search_string=search_string or "",
            limit=limit,
        )

    if search_type == "sampleData":
        if not title:
            raise ValueError("title is required for sampleData search type")
        return _sample_data_roles(
            db=db,
            title=title,
            company_id=company_id,
            search_string=search_string,
            limit=limit,
        )

    if search_type == "high_level_func":
        return _high_level_func(db, search_string, sub_level_func, limit)

    if search_type == "sub_level_func":
        return _sub_level_func(db, search_string, high_level_func, limit)

    config = AUTOCOMPLETE_REGISTRY.get(search_type)
    if not config:
        raise ValueError(f"Unsupported search type: {search_type}")

    effective_limit = config.get("default_limit", DEFAULT_LIMIT)
    if limit is not None:
        effective_limit = limit

    if config["style"] == DIRECT:
        return _run_direct(
            db, config, search_string, company_id, effective_limit
        )
    if config["style"] == MASTER_JOIN:
        return _run_master_join(
            db, config, search_string, company_id, effective_limit
        )
    if config["style"] == RAW:
        return _run_raw(db, config, search_string, effective_limit)

    raise ValueError(f"Unsupported search type: {search_type}")
