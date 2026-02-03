"""Role Adjacency using the LLM."""

import asyncio
import json
import random
from typing import List, Dict
from .types import RoleAdjacencyInput
import traceback
from .utils import (
    get_company_roles_and_job_descriptions,
    extract_tag_from_text,
    get_llm_based_role_description,
    artificial_score_scaling,
)
from .types import PredictedRole
from .exceptions import RoleAdjacencyException
from .utils import arequest_llm, request_llm


class RoleDescriptionNotFoundError(RoleAdjacencyException):
    pass


class RoleCandidateNotFoundError(RoleAdjacencyException):
    pass


class RoleLLMValidationFailedError(RoleAdjacencyException):
    pass


MAX_CONCURRENCY = 4


async def filter_adjacent_candidates(role: str, roles: List[str]) -> List[str]:
    """Filter the roles of the same family as the role"""
    filtered_candidates = []
    roles = list(set(roles))
    # print("Number of unique roles: ", len(roles))
    if len(roles) > 550:
        # TODO: this is a temporary fix to reduce the number of candidates to 550. We need to find a better way to do this.
        print(
            f"Filtering adjacent candidates because there are more than 550 candidates: {len(roles)}"
        )
        roles = random.sample(roles, 550)

    semphore = asyncio.Semaphore(MAX_CONCURRENCY)
    responses = []
    step = 100

    async def process_batch(batch: int):
        async with semphore:
            sub_roles = roles[batch : batch + step]
            response_content = await asyncio.wait_for(
                arequest_llm(
                    prompt_name="role_family_filtering",
                    placeholders={
                        "ROLE": role,
                        "ROLES": "\n".join([f"- {r}" for r in sub_roles]),
                    },
                ),
                timeout=120,
            )
            if response_content is not None:
                responses.append(response_content)

    # Process batches in parallel
    tasks = [process_batch(i) for i in range(0, len(roles), step)]
    await asyncio.gather(*tasks)

    for response_content in responses:
        extraced_sub_candidate_json_str = extract_tag_from_text(
            "json", response_content
        )
        if extraced_sub_candidate_json_str is None:
            print("Failed to extract JSON from response")
            continue
        filtered_sub_candidate = json.loads(extraced_sub_candidate_json_str)
        filtered_candidates.extend(filtered_sub_candidate)
    filtered_candidates = list(set(filtered_candidates))
    return filtered_candidates


def generate_similar_roles_using_llm(
    role: str,
    responsibilities: str,
    available_roles: List[str],
    *,
    top_k: int = 5,
) -> List[Dict[str, str]]:
    try:
        response_content = request_llm(
            prompt_name="role_similarity_analysis",
            placeholders={
                "ROLE": role,
                "RESPONSIBILITIES": responsibilities,
                "TOP_K": str(top_k),
                "AVAILABLE_ROLES": "\n".join([f"- {role}" for role in available_roles]),
            },
        )
        similar_roles_json_str = extract_tag_from_text("json", response_content)

        if similar_roles_json_str is None:
            raise Exception("Failed to extract similar roles data")

        # Parse JSON
        try:
            loaded_json = json.loads(similar_roles_json_str)
        except Exception:
            # print("output of the LLM: ", response_content)
            # print(f"Similar roles JSON string: {similar_roles_json_str}")
            raise Exception("Failed to parse similar roles data")
        return loaded_json
    except Exception as e:
        print(
            f"Error while using LLM to find similar roles for '{role}': ",
            e,
            flush=True,
        )
        traceback.print_exc()
        return None


def validate_llm_similar_roles_data(similar_roles_data: List[Dict[str, str]]) -> None:
    """Validate the similar roles data returned by the LLM"""

    # Validate the structure
    for role in similar_roles_data:
        if "role_name" not in role:
            raise RoleLLMValidationFailedError(
                f"Missing 'role_name' field for role: {role}"
            )
        if "similarity_score" not in role:
            raise RoleLLMValidationFailedError(
                f"Missing 'similarity_score' field for role: {role}"
            )
        if role["similarity_score"] < 0 or role["similarity_score"] > 100:
            raise RoleLLMValidationFailedError(
                f"Similarity score must be between 0 and 100 for role: {role}"
            )


def get_candidate_roles(data: RoleAdjacencyInput) -> List[str]:
    """Get candidate roles for a given role

    Args:
        data: Input containing the role and company information.
    Returns:
        List of candidate roles.

    Raises:
        RoleCandidateNotFoundError: If no candidate roles are found.
    """
    try:
        results = get_company_roles_and_job_descriptions(data["company"])
    except Exception as e:
        raise RoleCandidateNotFoundError(
            f"Failed to get candidate roles for role: {data['role']} in company: {data['company']}: {e}"
        )

    candidate_roles = [
        result["role_name"] for result in results if result["role_name"] != data["role"]
    ]
    candidate_roles = list(set(candidate_roles))
    if len(candidate_roles) == 0:
        raise RoleCandidateNotFoundError(
            f"No similar roles data found for role: {data['role']} in company: {data['company']}"
        )
    return candidate_roles


async def get_similar_roles_using_llm(data: RoleAdjacencyInput) -> List[PredictedRole]:
    """Get top similar roles for a given role using LLM

    Args:
        data: Input containing the role and company information.

    Returns:
        List of predicted roles and scores.

    Raises:
        RoleDescriptionNotFoundError: If no role data is found.
        RoleFamilyNotFoundError: If no job family is found.
        RoleCandidateNotFoundError: If no similar roles are found.
        RoleLLMValidationFailedError: If the similar roles data is invalid.
    """
    try:
        results = get_company_roles_and_job_descriptions(data["company"])
    except Exception as e:
        raise RoleCandidateNotFoundError(
            f"Failed to get candidate roles for role: {data['role']} in company: {data['company']}: {e}"
        )
    role_description = data.get("description", None)

    if role_description is None:
        try:
            for result in results:
                if result["role_name"] == data["role"]:
                    role_description = result["description"]
                    break
            if role_description is None:
                raise RoleDescriptionNotFoundError(
                    f"No role description found for role: {data['role']} in company: {data['company']}"
                )
        except Exception:
            try:
                role_data = get_llm_based_role_description(
                    data["role"], data["company"]
                )
            except Exception as e:
                raise RoleDescriptionNotFoundError(
                    f"Failed to get role description for role: {data['role']} in company: {data['company']}: {e}"
                )

            if len(role_data) == 0:
                raise RoleDescriptionNotFoundError(
                    f"No role description found for role: {data['role']} in company: {data['company']}"
                )
            role_description = role_data[0]["description"]

    # Setting the candiates
    candidate_roles = data.get("candidate_roles", None)
    candidate_roles = [
        result["role_name"] for result in results if result["role_name"] != data["role"]
    ]

    if candidate_roles is None or candidate_roles == []:
        raise RoleCandidateNotFoundError(
            f"No candidate roles found for role: {data['role']} in company: {data['company']}"
        )
    if len(candidate_roles) > 70:
        print(
            f"Filtering adjacent candidates because there are more than 70 candidates: {len(candidate_roles)}"
        )
        candidate_roles = await filter_adjacent_candidates(
            data["role"], candidate_roles
        )

    candidate_roles = list(set(candidate_roles))
    similar_roles_data = generate_similar_roles_using_llm(
        data["role"],
        role_description,
        candidate_roles,
        top_k=data["top_k"],
    )
    validate_llm_similar_roles_data(similar_roles_data)
    similar_roles_data = [
        PredictedRole(
            job_role=role["role_name"],
            score=artificial_score_scaling(role["similarity_score"]),
        )
        for role in similar_roles_data
    ]
    return similar_roles_data
