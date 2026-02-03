import hashlib
import traceback
from typing import Union, List, Final

from services.redis_store import redis_cache
from ml_models.role_adjacency import get_similar_roles, PredictedRole
from ml_models.role_adjacency.types import RoleAdjacencyInput
from common.logger import logger


def generate_role_adjacency_key(data: RoleAdjacencyInput, version: str = "v1") -> str:
    """Generate a key for the role adjacency cache."""
    key = f"{data['role']}:{data['company']}:{version}:{data.get('description', None)}:{data.get('candidate_roles', None)}"
    hash_key = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return f"role_adjacency:{hash_key}"


CACHE_EXPERATION_SECONDS: Final[int] = 60 * 60 * 24 * 30  # 30 days cache expiration


@redis_cache(
    hash_key_generator=generate_role_adjacency_key,
    cache_expiration_seconds=CACHE_EXPERATION_SECONDS,
)
def get_adjacent_roles_cacheable(
    data: RoleAdjacencyInput, version: str = "v1"
) -> Union[List[PredictedRole], str]:
    """Wrapper function to get adjacent roles from the cache."""
    try:
        return get_similar_roles(data, version)
    except Exception as e:
        logger.error(traceback.format_exc())
        raise e
