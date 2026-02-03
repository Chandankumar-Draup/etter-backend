"""Role adjacency functionality for skill mapping and analysis."""

import asyncio
from typing import List, Union

from .types import RoleAdjacencyInput, PredictedRole
from .title_to_role_api import get_similar_roles_using_title_to_role_api
from .role_adjacency_with_llm import get_similar_roles_using_llm
from .role_adjacency_with_embedding import get_similar_roles_using_embedding_model


async def get_similar_roles_async(
    data: RoleAdjacencyInput, version: str = "v1"
) -> Union[List[PredictedRole], str]:
    """Get similar roles for a given role (async version).

    Args:
        data: Input containing the role and company information.
        version: API version to use.

    Returns:
        List of title-to-role mapping results with predicted roles and scores.

    Raises:
        ValueError: If an unsupported version is specified.
        requests.RequestException: If the API request fails.
    """

    if version == "v1":
        similar_roles = get_similar_roles_using_title_to_role_api(data)
    elif version == "v2":
        similar_roles = await get_similar_roles_using_llm(data)
    elif version == "v3":
        similar_roles = get_similar_roles_using_embedding_model(data)
    else:
        raise ValueError(f"Unsupported version: {version}")

    return similar_roles


def get_similar_roles(
    data: RoleAdjacencyInput, version: str = "v1"
) -> Union[List[PredictedRole], str]:
    """Get similar roles for a given role.

    Args:
        data: Input containing the role and company information.
        version: API version to use (currently only "v1" supported).

    Returns:
        List of title-to-role mapping results with predicted roles and scores.

    Raises:
        ValueError: If an unsupported version is specified.
        requests.RequestException: If the API request fails.
    """

    if version == "v1":
        similar_roles = get_similar_roles_using_title_to_role_api(data)
    elif version == "v2":
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Cannot run async function in running event loop. Use get_similar_roles_async instead.")
            similar_roles = loop.run_until_complete(get_similar_roles_using_llm(data))
        except RuntimeError:
            similar_roles = asyncio.run(get_similar_roles_using_llm(data))
    elif version == "v3":
        similar_roles = get_similar_roles_using_embedding_model(data)
    else:
        raise ValueError(f"Unsupported version: {version}")

    return similar_roles
