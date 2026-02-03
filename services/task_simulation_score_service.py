import time
from typing import Set, Dict, List, Optional, Any
import requests
from requests import RequestException
from common.logger import logger
from ml_models.task_simulator import compute_task_simulator_scores
from ml_models.task_simulator import compute_etter_task_simulation_score
from settings.database import get_db
from services.etter import get_tasks_from_sources

def request_tasks_funciton_id(function_id: str) -> list[str]:
    """Fetch workflow names (tasks) for a given function id from ETTER endpoint."""

    url = "https://qa-etter.draup.technology/api/etter/get_workflows"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Origin": "https://qa-etter.draup.technology",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Mzk2NiwiZXhwIjoxNzY0MjU1NzYxLCJqdGkiOiJhZTMwNGY2Zi0wMThmLTQ0NDgtYWY0Ni1hMTI0YmFhYThhOTEifQ.3w-QqxT66_3CZhZNs6NUIb29Kvk1rrIuw1Yil5jP52w",
    }
    try:
        response = requests.get(
            url, headers=headers, params={"function_id": function_id}, timeout=10
        )
        if not response.ok:
            logger.error(
                f"request_tasks_funciton_id failed: status={response.status_code}, text={response.text}"
            )
            return []
        data = response.json()
    except (RequestException, ValueError) as exc:
        logger.error(f"request_tasks_funciton_id exception: {exc}")
        return []

    items = data.get("data") or []
    if not isinstance(items, list):
        logger.warning("request_tasks_funciton_id: unexpected data format for 'data'")
        return []

    results: list[str] = []
    for item in items:
        if isinstance(item, dict):
            name = item.get("workflow_name")
            if isinstance(name, str) and name.strip():
                results.append(name.strip())

    return results


def request_tasks_source(company: str, role: str) -> list[Dict[str, Any]]:
    """Fetch tasks for the given company and role using internal task sources.

    Returns:
        List of task dictionaries with 'task' and 'task_type' keys
    """

    db = get_db()
    try:
        result = get_tasks_from_sources(
            company=company,
            role=role,
            workflow_id=None,
            workflow_name=None,
            function_id=None,
            db=db
        )
    except Exception as exc:
        logger.error(f"request_tasks_source exception: {exc}")
        return []

    if not isinstance(result, dict):
        logger.warning("request_tasks_source: unexpected result type")
        return []

    if "error" in result:
        logger.error(f"request_tasks_source error: {result['error']}")
        return []

    tasks = result.get("tasks", [])
    if not isinstance(tasks, list):
        logger.warning("request_tasks_source: unexpected tasks format")
        return []

    cleaned_tasks = []
    for task in tasks:
        # Handle new dict format: {"task": "...", "task_type": "AI"}
        if isinstance(task, dict):
            task_name = task.get("task", "")
            task_type = task.get("task_type", "Human+AI")
            if task_name and isinstance(task_name, str):
                stripped = task_name.strip()
                if stripped:
                    # Preserve the full dict structure with task_type
                    cleaned_tasks.append({"task": stripped, "task_type": task_type})
        # Handle legacy string format for backward compatibility
        elif isinstance(task, str):
            stripped = task.strip()
            if stripped:
                # Wrap in dict format with default task_type
                cleaned_tasks.append({"task": stripped, "task_type": "Human+AI"})

    return cleaned_tasks


def request_company_tasks(company: str) -> dict:
    """Request the tasks for a given company."""

    url = "https://qa-etter.draup.technology/api/etter/get_workflows"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Origin": "https://qa-etter.draup.technology",
    }

    data = {
        "workflow": "task_consolidator",
        "username": "abhay.vashist@draup.com",
        "data": {"company": company, "previous_step": "save_ai_assessment", "is_edited": False},
        "company": company,
        "step": "get_consolidated_tasks",
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=20)
        if not response.ok:
            logger.error(
                f"request_company_tasks failed: status={response.status_code}, text={response.text}"
            )
            return {}
        return response.json()
    except (RequestException, ValueError) as exc:
        logger.error(f"request_company_tasks exception: {exc}")
        return {}


def process_task_from_api(data: dict, top_k: int = 20) -> list[str]:
    """Extract the top-k unique task names from a consolidated tasks response."""

    try:
        body = (
            data.get("current_step", {})
            .get("data", {})
            .get("consolidated_tasks_table", {})
            .get("body", [])
        )
        if not isinstance(body, list):
            logger.warning("process_task_from_api: 'body' is not a list")
            return []
    except Exception as exc:
        logger.error(f"process_task_from_api: error accessing body: {exc}")
        return []

    def get_occurrence(item: dict) -> int:
        # Support both 'occurrence' and 'Occurrence'
        value = None
        if isinstance(item, dict):
            value = item.get("occurrence", item.get("Occurrence", 0))
        try:
            return int(value) if value is not None else 0
        except (TypeError, ValueError):
            return 0

    sorted_items = sorted(body, key=get_occurrence, reverse=True)

    unique_tasks: Set[str] = set()
    for item in sorted_items:
        if not isinstance(item, dict):
            continue
        task_name = item.get("Task") or item.get("task")
        if isinstance(task_name, str) and task_name.strip():
            unique_tasks.add(task_name.strip())

    if top_k is None or top_k <= 0:
        return list(unique_tasks)
    return list(unique_tasks)[:top_k]


def get_top_k_tasks_from_company(company: str, top_k: int = 20) -> list[str]:
    """Get the top-k unique tasks for the given company using the consolidated table."""
    try:
        data = request_company_tasks(company)
        if not data:
            return []
        return process_task_from_api(data, top_k)
    except Exception as exc:
        logger.error(f"get_top_k_tasks_from_company exception: {exc}")
        return []


async def get_etter_task_simulation_score(llm_scores: list):
    csv_example = """# Example Input (for two tasks):
Task,Task Type,Average Model Score
Prepare monthly sales summary in Excel,AI,85
Draft a first-pass job description for a Data Analyst,Human+AI,47.5
"""
    try:
        task_and_scores = [{"task": task["task"], "score": task["mean_scores"], "task_type": task["task_type"]} for task in llm_scores]
        csv_input_str = "\n".join(["Task,Task Type,Average Model Score"] + [f"{task['task']},{task['task_type']},{task['score']}" for task in task_and_scores])
        res = await compute_etter_task_simulation_score(csv_input_str, csv_example)
    except Exception as e:
        logger.error(f"get_etter_task_simulation_score exception: {e}")
        return llm_scores

    if not isinstance(res, list):
        logger.warning(f"get_etter_task_simulation_score: expected list, got {type(res)}: {res}")
        return llm_scores

    res_lookup: Dict[str, Dict[str, Any]] = {}
    for item in res:
        if isinstance(item, dict) and 'task' in item:
            res_lookup[item['task']] = item

    for task in llm_scores:
        item = res_lookup.get(task['task'], {})
        task['model_task_results'].append({
            "model": "etter", 
            "score": item.get('score', 0), 
            "reason": item.get('reason', '')
            })
    return llm_scores


async def compute_task_simulator_scores_service(
    tasks: List[str], company: Optional[str] = None, role: Optional[str] = None
) -> list:
    """Generate simulator scores after merging remote and provided task inputs.

    Args:
        tasks: Explicit task names that should be included in scoring.
        company: Company name to fetch tasks for via the ETTER task source API.
        role: Role name paired with the company when requesting remote tasks.

    Returns:
        list: Simulator scoring results for the consolidated task list, including task_type.

    Raises:
        None.
    """
    if not tasks and not company and not role:
        return []

    # Fetch tasks from source (returns list of dicts with task and task_type)
    task_dicts: List[Dict[str, Any]] = request_tasks_source(company, role)
    # Limit the number of tasks to 20 if role is not provided
    if role is None:
        task_dicts = task_dicts[:20]

    # Build task metadata mapping: {task_name: task_type}
    task_metadata: Dict[str, str] = {}
    for task_dict in task_dicts:
        task_name = task_dict.get("task", "")
        task_type = task_dict.get("task_type", "Human+AI")
        if task_name:
            task_metadata[task_name] = task_type

    # Extract task names for aggregation
    aggregated_task_names: List[str] = [t.get("task", "") for t in task_dicts if t.get("task")]

    # Add user-provided tasks (default to Human+AI type)
    if tasks:
        for task in tasks:
            if task and task not in task_metadata:
                task_metadata[task] = "Human+AI"
            aggregated_task_names.append(task)

    # Deduplicate task names
    aggregated_task_names = list(set(aggregated_task_names))

    try:
        time_start = time.perf_counter()
        llm_scores = await compute_task_simulator_scores(aggregated_task_names, task_metadata=task_metadata)
        time_end = time.perf_counter()
        total_time = time_end - time_start
        logger.info(f"compute_task_simulator_scores executed in {total_time:.4f} seconds.")
        etter_scores = await get_etter_task_simulation_score(llm_scores)
        return etter_scores
    except Exception as exc:
        logger.error(f"compute_task_simulator_scores_service failed: {exc}")
        return []
