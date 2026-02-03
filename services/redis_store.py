"""Wrapper around the redis client"""

from logging import warn
from os import environ
from typing import Final, Optional, cast, Callable, Any, Dict
import json

from common.logger import logger

CACHE_EXPERATION_SECONDS: Final[int] = int(environ.get("CACHE_EXPERATION_SECONDS", 3600))

REDIS_DB: Final[int] = int(environ.get("REDIS_DB", 14))
REDIS_PORT: Final[int] = int(environ.get("REDIS_PORT", 6379))
REDIS_HOST: Final[str] = environ.get("REDIS_RW_HOST", "localhost")
REDIS_PASSWORD: Final[Optional[str]] = environ.get("REDIS_PASSWORD", None)


class RedisClient:
    def __init__(self, host="localhost", port=6379, db=0, password=None):
        import redis

        self.redis = redis.Redis(host=host, port=port, db=db, password=password)
        self.redis.ping()

    def set(self, key: str, value: str) -> None:
        self.redis.set(key, value)

    def get(self, key: str) -> Optional[str]:
        return cast(Optional[str], self.redis.get(key))

    def exists(self, key) -> bool:
        return cast(bool, self.redis.exists(key))

    def setex(self, key: str, exp_seconds: int, value: str) -> None:
        self.redis.setex(key, exp_seconds, value)

    def delete(self, key: str) -> None:
        self.redis.delete(key)

    def ping(self) -> bool:
        return self.redis.ping()

    def hset(self, key: str, field: str, value: str) -> None:
        self.redis.hset(key, field, value)

    def hget(self, key: str, field: str) -> Optional[str]:
        return cast(Optional[str], self.redis.hget(key, field))


redis_client = None
redis_qa_login_client = None


def get_redis_client() -> RedisClient:
    """
    Getting the redis client based on system configuration
    """
    global redis_client
    if redis_client is None:
        redis_client = RedisClient(
            host=REDIS_HOST, password=REDIS_PASSWORD, port=REDIS_PORT, db=REDIS_DB
        )
    return redis_client


def get_redis_qa_login_client() -> RedisClient:
    """
    Getting the redis client for QA login caching
    """
    global redis_qa_login_client
    if redis_qa_login_client is None:
        redis_qa_login_client = RedisClient(
            host=REDIS_HOST,
            password=REDIS_PASSWORD,
            port=REDIS_PORT,
            db=15,
        )
    return redis_qa_login_client


def redis_cache(
    hash_key_generator: Callable, cache_expiration_seconds: int = CACHE_EXPERATION_SECONDS
) -> Callable:
    """
    Redis cache decorator with graceful fallback on Redis failures.
    If Redis is unavailable, the decorator will fall back to calling the function directly.
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            """
            Wrapping the function with the cache decorator
            """
            key = hash_key_generator(*args, **kwargs)
            try:
                redis_client = get_redis_client()

                # Try to get cached result
                if redis_client.exists(key):
                    cached_value = redis_client.get(key)
                    if cached_value:
                        logger.info(f"Cache hit for key: {key}")
                        return json.loads(cached_value)

                # Cache miss - call the function
                logger.info(f"Cache miss for key: {key}")
                result = func(*args, **kwargs)

                # Try to cache the result
                try:
                    redis_client.setex(key, cache_expiration_seconds, json.dumps(result))
                except Exception as cache_error:
                    # Log but don't fail if we can't cache the result
                    logger.warning(f"Failed to cache result for key {key}: {str(cache_error)}")

                return result

            except Exception as redis_error:
                # Redis is unavailable - log and fall back to calling the function
                logger.warning(
                    f"Redis error for key {key}, falling back to direct function call: {str(redis_error)}"
                )
                return func(*args, **kwargs)

        return wrapper

    return decorator


def add_cache_data(redis_client: RedisClient, redis_key: str, field: str, metadata: Any) -> None:
    """
    Add data to a redis key
    :param redis_key: The key to add the data to
    :param redis_client: The redis client to use
    :param field: The field to add the data to
    :param metadata: The metadata to use to get the data
    :return: None
    """
    data = None
    try:
        if metadata:
            if isinstance(metadata, dict):
                data = metadata
            else:
                data = metadata

        if data:
            redis_client.hset(redis_key, field, json.dumps(data))
    except Exception as e:
        logger.error(f"Error in add_cache_data: {str(e)}")


def get_cache_data(
    redis_client: RedisClient, redis_key: str, field: Optional[str] = None, is_set: bool = False
) -> Optional[Any]:
    """
    Get data from a redis key
    :param redis_key: The key to get the data from
    :param redis_client: The redis client to use
    :param field: The field to get the data from
    :param is_set: Whether the data is a set
    :return: The data from the redis key
    """
    try:
        if field:
            data = redis_client.hget(redis_key, field)
        else:
            data = redis_client.get(redis_key)

        if data:
            if is_set:
                return set(json.loads(data))
            else:
                parsed_data = json.loads(data)
                return parsed_data
        return None
    except Exception as e:
        logger.error(f"Error in get_cache_data: {str(e)}")
        return None
