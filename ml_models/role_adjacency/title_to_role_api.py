"""Title to role API for role adjacency analysis."""

import requests
from typing import List, cast, Dict
from .types import RoleAdjacencyInput, PredictedRole, TitleToRoleResponse

from .exceptions import RoleAdjacencyException


class TitleToRoleAPIException(RoleAdjacencyException):
    pass


def get_similar_roles_using_title_to_role_api(
    data: RoleAdjacencyInput,
) -> List[PredictedRole]:
    """Fetch skill mappings using the title-to-role API.

    Args:
        data: Input containing the role and company information.

    Returns:
        List of predicted roles and scores.

    Raises:
        requests.RequestException: If the API request fails.
        ValueError: If the response format is invalid.
    """

    try:
        api_response = get_title_to_role_api(data["role"], data["top_k"])
    except Exception as e:
        raise TitleToRoleAPIException(
            f"Error while getting similar roles using title to role API: {e}"
        )

    if not api_response:
        raise TitleToRoleAPIException(f"No API response found")
    if "results" not in api_response:
        raise TitleToRoleAPIException(f"No results found in API response")

    if len(api_response["results"]) == 0:
        raise TitleToRoleAPIException(f"No results found in API response")

    if "predicted_roles" not in api_response["results"][0]:
        raise TitleToRoleAPIException(f"No predicted roles found in API response")

    api_response = cast(TitleToRoleResponse, api_response)
    predicted_roles = api_response["results"][0]["predicted_roles"]
    predicted_roles = [role for role in predicted_roles if role["job_role"] != data["role"]]
    predicted_roles = [
        PredictedRole(job_role=role["job_role"], score=round(role["score"] * 100, 2))
        for role in predicted_roles
    ]
    return predicted_roles


def get_title_to_role_api(role: str, top_k: int) -> Dict:
    """Get title to role API.

    Args:
        role: The role to get similar roles for.
        top_k: The number of top roles to return.

    Returns:
        List of predicted roles and scores.
    """

    try:
        base_url = "http://127.0.0.1:8080"
        request_data = {
            "input_titles": [role],
            "top_k": top_k,
            "return_score": True,
            "base_threshold": False,
        }
        response = requests.post(
            f"{base_url}/title-to-role",
            headers={"Content-Type": "application/json", "charset": "utf-8"},
            json=request_data,
        )

        # Raise an exception for bad status codes
        response.raise_for_status()

        return response.json()

    except Exception as e:
        print(e)
        return None
