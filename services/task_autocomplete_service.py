"""
Task Autocomplete Service

Provides autocomplete functionality for tasks using PostgreSQL cache with GIN indexes.
Tasks are cached from role_assessment_data workflow and can be refreshed on-demand or via scheduled jobs.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, and_

from models.etter import TaskAutocompleteCache, SampleData
from services.etter import get_tasks_from_sources

logger = logging.getLogger(__name__)


def fetch_tasks_autocomplete(
    db: Session,
    company: str,
    role: str,
    search_string: str,
    task_type: Optional[str] = None,
    limit: int = 10  # Deprecated: limit is hardcoded to 50 in SQL query
) -> List[Dict[str, Any]]:
    """
    Fetch task autocomplete suggestions using PostgreSQL GIN index.

    Note: Returns maximum 50 results (hardcoded in SQL query).

    Args:
        db: Database session
        company: Company name (required)
        role: Role name (required)
        search_string: Prefix to search for
        task_type: Optional task type filter (Human + AI, Human, AI)
        limit: Deprecated parameter (ignored, limit is hardcoded to 50)

    Returns:
        List of dictionaries with task_name and task_type (max 50 results)
    """
    try:
        # Check if cache exists and is fresh
        if check_cache_staleness(db, company, role):
            logger.info(f"Cache is stale for {company}+{role}, refreshing...")
            refresh_task_autocomplete_cache(db, company, role)

        # Query using GIN index for fast prefix matching
        # Build query with optional task_type filter
        task_type_filter = ""
        if task_type:
            task_type_filter = "AND task_type = :task_type"

        query = text(f"""
            SELECT task_name, task_type FROM (
                SELECT DISTINCT task_name, task_type
                FROM etter.etter_task_autocomplete_cache
                WHERE company = :company
                  AND role = :role
                  AND task_name ILIKE :search_pattern
                  {task_type_filter}
            ) AS distinct_tasks
            ORDER BY
                LENGTH(task_name) ASC,  -- Shorter matches first (more relevant)
                task_name ASC           -- Alphabetical for ties
            LIMIT 50
        """)

        params = {
            'company': company,
            'role': role,
            'search_pattern': f"{search_string}%",  # Prefix matching
        }
        if task_type:
            params['task_type'] = task_type

        result = db.execute(query, params)

        tasks = [{'task_name': row[0], 'task_type': row[1]} for row in result]
        logger.info(f"Found {len(tasks)} autocomplete matches for '{search_string}' ({company}+{role}, task_type={task_type})")

        return tasks

    except Exception as e:
        logger.error(f"Error fetching task autocomplete: {str(e)}")
        # Return empty list on error rather than raising
        return []


def refresh_task_autocomplete_cache(
    db: Session,
    company: str,
    role: str,
    is_autocomplete: bool = False
) -> Dict[str, Any]:
    """
    Refresh task autocomplete cache for a specific company+role combination.
    Fetches ALL tasks from role_assessment_data (not just top 20) and upserts into cache.

    Args:
        db: Database session
        company: Company name
        role: Role name

    Returns:
        Dictionary with status and count of tasks cached
    """
    try:
        db.rollback()  # Force clear transaction state
        logger.info(f"Rolled back transaction for {company}+{role}")
        logger.info(f"Refreshing task cache for {company}+{role}")

        # Fetch ALL tasks from role_assessment_data (not limited to 20)
        tasks_data = get_tasks_from_sources(
            company=company,
            role=role,
            workflow_id=None,
            workflow_name=None,
            function_id=None,
            db=db,
            limit=None,       # Get ALL tasks
            is_autocomplete=is_autocomplete
        )

        # Check for errors
        if 'error' in tasks_data:
            logger.error(f"Failed to fetch tasks: {tasks_data.get('error')}")
            return {
                'status': 'error',
                'error': tasks_data.get('error'),
                'error_code': tasks_data.get('error_code')
            }

        # Extract tasks list
        tasks = tasks_data.get('tasks', [])
        if not tasks:
            logger.warning(f"No tasks found for {company}+{role}")
            return {
                'status': 'success',
                'company': company,
                'role': role,
                'tasks_cached': 0,
                'message': 'No tasks found'
            }

        # Upsert tasks into cache table
        tasks_cached = 0
        for task_dict in tasks:
            task_name = task_dict.get('task')
            task_type = task_dict.get('task_type')

            if not task_name:
                continue

            # Use raw SQL for efficient upsert
            upsert_query = text("""
                INSERT INTO etter.etter_task_autocomplete_cache
                    (task_name, company, role, task_type, source, updated_at)
                VALUES
                    (:task_name, :company, :role, :task_type, :source, NOW())
                ON CONFLICT (task_name, company, role)
                DO UPDATE SET
                    task_type = EXCLUDED.task_type,
                    source = EXCLUDED.source,
                    updated_at = NOW()
            """)

            db.execute(upsert_query, {
                'task_name': task_name,
                'company': company,
                'role': role,
                'task_type': task_type,
                'source': 'role_assessment_data'
            })
            tasks_cached += 1

        db.commit()

        logger.info(f"Successfully cached {tasks_cached} tasks for {company}+{role}")

        return {
            'status': 'success',
            'company': company,
            'role': role,
            'tasks_cached': tasks_cached,
            'tasks': tasks,
            'source': tasks_data.get('source')
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error refreshing task cache for {company}+{role}: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'company': company,
            'role': role
        }


def refresh_all_task_autocomplete_cache(db: Session) -> Dict[str, Any]:
    """
    Refresh task autocomplete cache for ALL known company+role combinations.
    Used by daily scheduled job.

    Args:
        db: Database session

    Returns:
        Summary dict with total, successful, and failed counts
    """
    try:
        logger.info("Starting batch refresh of all task autocomplete caches")

        # Get all known company+role combinations
        combinations = get_known_company_role_combinations(db)

        if not combinations:
            logger.warning("No company+role combinations found to refresh")
            return {
                'status': 'success',
                'total_combinations': 0,
                'successful': 0,
                'failed': 0,
                'results': []
            }

        results = []
        successful = 0
        failed = 0

        for company, role in combinations:
            try:
                result = refresh_task_autocomplete_cache(db, company, role)
                if result.get('status') == 'success':
                    successful += 1
                else:
                    failed += 1
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to refresh {company}+{role}: {str(e)}")
                failed += 1
                results.append({
                    'status': 'error',
                    'company': company,
                    'role': role,
                    'error': str(e)
                })

        logger.info(f"Batch refresh complete: {successful} successful, {failed} failed out of {len(combinations)} total")

        return {
            'status': 'success',
            'total_combinations': len(combinations),
            'successful': successful,
            'failed': failed,
            'results': results
        }

    except Exception as e:
        logger.error(f"Error in batch refresh: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'total_combinations': 0,
            'successful': 0,
            'failed': 0
        }


def get_known_company_role_combinations(db: Session) -> List[Tuple[str, str]]:
    """
    Get all unique (company, role) combinations from the system.
    Queries the etter_sampledata table which tracks all company+role pairs.

    Args:
        db: Database session

    Returns:
        List of (company, role) tuples
    """
    try:
        # Query unique combinations from sampledata table
        # Join with iris1_mastercompany to get company names
        query = text("""
            SELECT DISTINCT
                mc.company_name,
                sd.role
            FROM etter.etter_sampledata sd
            INNER JOIN iris1.iris1_mastercompany mc ON sd.company_id = mc.id
            WHERE sd.company_id IS NOT NULL
              AND mc.company_name IS NOT NULL
              AND sd.role IS NOT NULL
            ORDER BY mc.company_name, sd.role
        """)

        result = db.execute(query)
        combinations = [(row[0], row[1]) for row in result]

        logger.info(f"Found {len(combinations)} unique company+role combinations")

        return combinations

    except Exception as e:
        logger.error(f"Error fetching company+role combinations: {str(e)}")
        return []


def check_cache_staleness(
    db: Session,
    company: str,
    role: str,
    max_age_days: int = 1
) -> bool:
    """
    Check if cache for a company+role needs refresh.
    Returns True if cache is stale (older than max_age_days or doesn't exist).

    Args:
        db: Database session
        company: Company name
        role: Role name
        max_age_days: Maximum age in days before cache is considered stale (default 1)

    Returns:
        True if cache is stale and needs refresh, False otherwise
    """
    try:
        # Check if any tasks exist for this company+role and when they were last updated
        query = text("""
            SELECT MAX(updated_at) as last_update
            FROM etter.etter_task_autocomplete_cache
            WHERE company = :company
              AND role = :role
        """)

        result = db.execute(query, {
            'company': company,
            'role': role
        }).fetchone()

        if not result or not result[0]:
            # No cache exists
            logger.info(f"No cache found for {company}+{role}")
            return True

        last_update = result[0]
        age = datetime.utcnow() - last_update

        if age > timedelta(days=max_age_days):
            logger.info(f"Cache for {company}+{role} is {age.days} days old (stale)")
            return True

        logger.debug(f"Cache for {company}+{role} is fresh ({age.seconds // 3600} hours old)")
        return False

    except Exception as e:
        logger.error(f"Error checking cache staleness: {str(e)}")
        # On error, assume cache is stale to trigger refresh
        return True
