"""Utils for role adjacency analysis."""

import re
from requests import post
from typing import Dict, List, Optional
from draup_packages.draup_llm_manager import DraupLLMManager
from common.logger import logger
from constants.auth import ENV, DRAUP_LLM_USER
from constants.llm_models import (
    ROLE_ADJACENCY_MODEL_CONFIG,
    ROLE_ADJACENCY_FALLBACK_MODEL_CONFIG,
)


model_config = ROLE_ADJACENCY_MODEL_CONFIG
fallback_models = ROLE_ADJACENCY_FALLBACK_MODEL_CONFIG
# LLM client configuration
LLM_ENV: str = ENV
LLM_USER: str = DRAUP_LLM_USER
LLM_PROCESS: str = "testing"
LLM_TEMPERATURE: float = 0.0
LLM_TIMEOUT_SECONDS: int = 60


async def arequest_llm(
    prompt_name: str, placeholders: Dict, config: Optional[Dict] = None
) -> Optional[str]:
    """
    Sends a request to the primary LLM using prompt_name and placeholders.
    If it fails, tries a fallback LLM provider.

    Args:
        prompt_name: Name of the prompt template to use.
        placeholders: Dictionary of placeholder values for the prompt template.
        config: Optional configuration dict. If not provided, uses default model_config.

    Returns:
        The LLM's response content as a string, or None if both attempts fail.
    """
    # Use provided config or default model_config
    if config is None:
        config = model_config

    # Prepare LLM clients
    llm_client = DraupLLMManager(
        env=LLM_ENV, user=LLM_USER, llm_provider=config["provider"], process=LLM_PROCESS
    )
    fallback_client = DraupLLMManager(
        env=LLM_ENV,
        user=LLM_USER,
        llm_provider=fallback_models["provider"],
        process=LLM_PROCESS,
    )

    # Attempt primary provider, fall back to secondary provider cleanly
    response = None
    primary_error = None
    try:
        response = await llm_client.acompletion(
            model=config["model"],
            prompt_name=prompt_name,
            placeholders=placeholders,
            temperature=LLM_TEMPERATURE,
            timeout=LLM_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.error(f"Error calling the LLM (primary: {exc})")
        primary_error = exc

    if response is not None:
        return response["choices"][0]["message"]["content"]

    # Primary failed, try fallback
    fallback_error = None
    try:
        response = await fallback_client.acompletion(
            model=fallback_models["model"],
            prompt_name=prompt_name,
            placeholders=placeholders,
            temperature=LLM_TEMPERATURE,
            timeout=LLM_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        fallback_error = exc

    if response is not None:
        return response["choices"][0]["message"]["content"]
    else:
        logger.error(f"Error calling the LLM (fallback: {fallback_error})")
        return None


def request_llm(
    prompt_name: str, placeholders: Dict, config: Optional[Dict] = None
) -> Optional[str]:
    """
    Sends a request to the LLM using prompt_name and placeholders.

    Args:
        prompt_name: Name of the prompt template to use.
        placeholders: Dictionary of placeholder values for the prompt template.
        config: Optional configuration dict. If not provided, uses default model_config.

    Returns:
        The LLM's response content as a string, or None if both attempts fail.
    """

    # Use provided config or default model_config
    if config is None:
        config = model_config

    # Prepare LLM clients
    llm_client = DraupLLMManager(
        env=LLM_ENV, user=LLM_USER, llm_provider=config["provider"], process=LLM_PROCESS
    )
    fallback_client = DraupLLMManager(
        env=LLM_ENV,
        user=LLM_USER,
        llm_provider=fallback_models["provider"],
        process=LLM_PROCESS,
    )

    # Attempt primary provider, fall back to secondary provider cleanly
    response = None
    primary_error = None
    try:
        response = llm_client.completion(
            model=config["model"],
            prompt_name=prompt_name,
            placeholders=placeholders,
            temperature=LLM_TEMPERATURE,
            timeout=LLM_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.error(f"Error calling the LLM (primary: {exc})")
        primary_error = exc

    if response is not None:
        return response["choices"][0]["message"]["content"]

    # Primary failed, try fallback
    fallback_error = None
    try:
        response = fallback_client.completion(
            model=fallback_models["model"],
            prompt_name=prompt_name,
            placeholders=placeholders,
            temperature=LLM_TEMPERATURE,
            timeout=LLM_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        fallback_error = exc

    if response is not None:
        return response["choices"][0]["message"]["content"]
    else:
        logger.error(f"Error calling the LLM (fallback: {fallback_error})")
        return None


def extract_tag_from_text(tag: str, text: str) -> str:
    """Extract content between XML-style tags from text."""
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    if match:
        cleaned_response = match.group(1).strip()
    else:
        cleaned_response = re.sub(rf"<{tag}>\s*|\s*</{tag}>", "", text.strip())

    return cleaned_response


def artificial_score_scaling(score: float) -> float:
    """
    Scale embedding similarity scores with piecewise linear scaling:
    - 90%+ (90+) → 80-90 (0.80-0.90)
    - 60-89% (60-89) → 55-80 (0.55-0.80)
    - < 60% (< 60) → 0-55 (0.00-0.55)

    Args:
        score: Original similarity score (expected range: 0.945 to 0.999)

    Returns:
        Scaled score in range [0.05, 0.40]
    """

    # Piecewise linear scaling
    if score >= 90:
        # Map [0.90, 1.0] to [0.80, 90]
        scaled_score = score * 0.8 + 8
    elif score >= 60:
        # Map [60 - 90] to [0.55 - 0.80]
        scaled_score = score * 0.88 + 5
    else:
        # Map [0.945, 0.96) to [0.05, 0.20]
        scaled_score = score * 0.95

    return scaled_score


def get_llm_based_role_description(role: str, company: str) -> List[Dict[str, str]]:
    """Get the role description from the llm.

    Args:
        role: The role to get the description for.
        company: The company to get the description for.
    Returns:
        The role description.
    Raises:
        ValueError: If the LLM request fails and no description is returned.
    """
    description = request_llm(
        prompt_name="role_description_generation",
        placeholders={"ROLE": role, "COMPANY": company},
    )
    if description is None:
        raise ValueError(
            f"Failed to get role description from LLM for role: {role} at company: {company}"
        )
    return [{"description": description, "job_role": role}]


def get_role_description_from_api(role: str, company: str) -> List[Dict[str, str]]:
    """Get the role description from the api.

    Args:
        role: The role to get the description for.
        company: The company to get the description for.
    Returns:
        The role description.
    Raises:
        Exception: If the role description is not found.
    """
    if company == "Acme Corporation":
        print("Warning: Company is Acme Corporation, replacing with Walmart Inc.")
        company = "Walmart Inc."
    """Get the role description from the api."""
    res = post(
        url="https://qa-draup-world.draup.technology/api/get_jd",
        headers={
            "origin": "https://draup-world.draup.technology",
            "Content-Type": "application/json",
            "charset": "utf-8",
        },
        json={"roles": role, "company": company},
    )

    if res.status_code != 200:
        raise Exception(f"Failed to get role description from api: {res.text}")

    data = res.json()["data"]
    if len(data) == 0:
        raise Exception(
            f"No role description found for role: {role} in company: {company}"
        )

    description = " ".join(data[0]["responsibilities"])
    return [{"description": description, "job_role": role}]


def get_company_assessment_data(company_name: str):
    """Get the company assessment data from the api.

    Args:
        company_name: The name of the company to get the assessment data for.
    Returns:
        The company assessment data.
    Raises:
        Exception: If the company assessment data is not found.
    """

    res = post(
        "https://qa-draup-world.draup.technology/api/workflows",
        headers={
            "content-type": "application/json",
            "origin": "https://draup-world.draup.technology",
            "charset": "utf-8",
        },
        json={
            "workflow": "role_assessment_data",
            "step": "get_company_assessment_data",
            "data": {"company": company_name, "include_history": False},
        },
    )

    if res.status_code != 200:
        raise Exception(f"Failed to get company assessment data from api: {res.text}")

    return res.json()


def get_company_roles_and_job_descriptions(company_name: str) -> List[Dict[str, str]]:
    """
    Get the company roles and job descriptions from the api.
    Args:
        company_name: The name of the company to get the roles and descriptions for.
    Returns:
        The company roles and job descriptions.
    Raises:
        Exception: If the company roles and job descriptions are not found.
        Exception: If the company assessment data is not found.
        Exception: If the company roles and job descriptions are not found.
    """
    res = get_company_assessment_data(company_name)
    if "error_code" in res:
        raise Exception(res["message"])

    if "current_step" not in res or "data" not in res["current_step"]:
        raise Exception("No data found")

    data = res["current_step"]["data"]
    if "roles_data" not in data:
        raise Exception("No role data found")

    roles = []
    for role in data["roles_data"]:
        try:
            role_str = role.get("role")
        except Exception:
            print("skipping role because no role name found: ", role)
            continue

        try:
            role_description = (
                role.get("assessment_data")
                .get("current_version")
                .get("job_description")
                .get("job_description")
            )
        except Exception:
            role_description = ""

        roles.append({"role_name": role_str, "description": role_description})

    return roles
