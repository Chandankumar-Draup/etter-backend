import asyncio
import json
from statistics import mean, variance
from typing import Optional, List, Dict, Any

from common.logger import logger
from constants.llm_models import (
    TASK_SIMULATOR_MODEL_CONFIGS,
    ETTER_SCORING_MODEL_CONFIGS,
)

from .utils import request_llm, extract_tag_from_text, extract_tag_from_markdown


async def _run_parallel_requests(
    model_configs: list[dict[str, str]],
    max_concurrency: int = 4,
) -> list:
    """Run LLM requests with bounded concurrency to avoid rate limits.

    Args:
        model_configs: A list of model configuration dicts to call. Each config must contain:
            - "model": model name
            - "provider": provider name
            - "prompt_name": prompt template name
            - "placeholders": dict of placeholder values
        max_concurrency: Maximum number of in-flight requests.
    """

    for model_config in model_configs:
        if "model" not in model_config or "provider" not in model_config:
            raise ValueError(
                "Model configuration must contain 'model' and 'provider' keys"
            )
        if "prompt_name" not in model_config:
            raise ValueError("Model configuration must contain 'prompt_name' key")
        if "placeholders" not in model_config:
            raise ValueError("Model configuration must contain 'placeholders' key")

    semaphore = asyncio.Semaphore(max_concurrency)

    async def call_model(model_config: dict):
        async with semaphore:
            logger.debug("Task simulator request config: %s", model_config)
            timeout = model_config.get("timeout", 180)
            try:
                response = await asyncio.wait_for(
                    request_llm(
                        prompt_name=model_config["prompt_name"],
                        placeholders=model_config["placeholders"],
                        config=model_config,
                    ),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "Task simulator request timed out for model %s with provider %s",
                    model_config.get("model"),
                    model_config.get("provider"),
                )
                return None
            except Exception as exc:
                logger.error(
                    "Task simulator request failed for model %s with provider %s: %s",
                    model_config.get("model"),
                    model_config.get("provider"),
                    exc,
                )
                return None

            if response is None:
                return None

            return {
                "model": model_config["model"],
                "provider": model_config["provider"],
                "response": response,
            }

    tasks = [asyncio.create_task(call_model(cfg)) for cfg in model_configs]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for item in raw_results:
        if isinstance(item, Exception) or item is None:
            continue
        results.append(item)
    return results


def parse_json_from_llm_response(text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from LLM response.
    
    Args:
        text: The text to parse JSON from.

    Returns:
        A dictionary of the parsed JSON, or None if the JSON is not valid.
    """
    try:
        response_json = extract_tag_from_text(text, "json")
        response_json = json.loads(response_json)
        return response_json
    except ValueError:
        try:
            response_json = extract_tag_from_markdown(text, "json")
            response_json = json.loads(response_json)
            return response_json
        except Exception as e:
            logger.error(
                f"Raw response from model: {text}, error: {e}"
            )
            return None


async def get_llm_scores_for_tasks(
    tasks: List[str], task_metadata: Optional[Dict[str, str]] = None
) -> list:
    """Run the task simulator."""
    task_content = "\n".join(
        ["Task,Task Type"]
        + [f"{task},{task_metadata.get(task, 'Human+AI')}" for task in tasks]
    )
    
    model_configs = [config.copy() for config in TASK_SIMULATOR_MODEL_CONFIGS]
    for config in model_configs:
        config["placeholders"] = {"TASK_CONTENT": task_content}

    responses = await _run_parallel_requests(model_configs)
    response_json = None
    for response in responses:
        if response["response"] is None:
            continue
        response_json = parse_json_from_llm_response(response["response"])
        if response_json is None:
            continue
        response["task_scores"] = response_json

    return responses


async def compute_task_simulator_scores(
    tasks: List[str], task_metadata: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """Compute summary statistics for task automation scores across LLMs.

    Args:
        tasks: List of task names to score
        task_metadata: Optional dict mapping task names to task types (Human+AI, Human, AI)

    Steps:
    1. Fetch raw LLM scores for the provided tasks.
    2. Aggregate scores per task across all models.
    3. Compute mean and variance per task.
    4. Return a structured list for each task with per-model scores and task_type.
    """
    llm_results = await get_llm_scores_for_tasks(tasks, task_metadata)

    # Pre-index per-model task scores for cleaner lookups
    per_model_task_scores: List[Dict[str, Any]] = []
    for model_result in llm_results:
        task_scores = model_result.get("task_scores") or []
        task_score_by_name = {
            item["task"]: item["score"]
            for item in task_scores
            if "task" in item and "score" in item
        }

        task_reason_by_name = {
            item["task"]: item["reason"]
            for item in task_scores
            if "task" in item and "reason" in item
        }
        per_model_task_scores.append(
            {
                "model": model_result.get("model"),
                "task_score_by_name": task_score_by_name,
                "task_reason_by_name": task_reason_by_name,
            }
        )

    results: List[Dict[str, Any]] = []
    for task in tasks:
        scores: List[int] = []
        model_task_results: List[Dict[str, Any]] = []

        for model_entry in per_model_task_scores:
            model_name = model_entry["model"]
            task_score_by_name = model_entry["task_score_by_name"]
            task_reason_by_name = model_entry["task_reason_by_name"]
            if task in task_score_by_name:
                score = task_score_by_name[task]
                reason = task_reason_by_name.get(task, "")
                model_task_results.append({"model": model_name, "score": score, "reason": reason})
                scores.append(score)

        if scores:
            mean_scores = mean(scores)
            # Sample variance requires at least two data points; default to 0.0 otherwise
            variances = variance(scores) if len(scores) > 1 else 0.0
        else:
            mean_scores = 0.0
            variances = 0.0

        results.append(
            {
                "task": task,
                "task_type": task_metadata.get(task, "Human+AI")
                if task_metadata
                else None,
                "mean_scores": mean_scores,
                "variances": variances,
                "model_task_results": model_task_results,
            }
        )

    return results


async def compute_etter_task_simulation_score(
    task_scores_str: str, input_example: str
) -> List[dict]:
    """Compute the task simulation score using the task type and score"""

    model_configs = [config.copy() for config in ETTER_SCORING_MODEL_CONFIGS]
    for config in model_configs:
        config["placeholders"] = {
            "MODEL_TASK_SCORES": task_scores_str,
            "INPUT_EXAMPLE": input_example,
        }
    response = await request_llm(
        prompt_name=model_configs[0]["prompt_name"],
        placeholders=model_configs[0]["placeholders"],
        config=model_configs[0],
    )
    logger.debug(f"Response from {model_configs[0]['model']}: {response}")
    if response is not None:
        try:
            response_json = extract_tag_from_text(response, "json")
            parsed_response = json.loads(response_json)
            if isinstance(parsed_response, list):
                return parsed_response
            else:
                logger.warning(f"Response from {model_configs[0]['model']} is not a list: {type(parsed_response)}")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse JSON from {model_configs[0]['model']}: {e}, raw response: {response_json if 'response_json' in locals() else response}")

    response = await request_llm(
        prompt_name=model_configs[1]["prompt_name"],
        placeholders=model_configs[1]["placeholders"],
        config=model_configs[1],
    )
    logger.debug(
        f"Fallback model response from {model_configs[1]['model']}: {response}"
    )
    if response is not None:
        try:
            response_json = extract_tag_from_text(response, "json")
            parsed_response = json.loads(response_json)
            if isinstance(parsed_response, list):
                return parsed_response
            else:
                logger.warning(f"Response from {model_configs[1]['model']} is not a list: {type(parsed_response)}")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse JSON from {model_configs[1]['model']}: {e}, raw response: {response_json if 'response_json' in locals() else response}")

    raise Exception("Failed to compute task simulation score")
