from typing import Dict, Optional, Final, cast
from os import environ

from ml_models.simulation import Store, SimulationStore

sim_store = None
CACHE_EXPERATION_SECONDS: Final[int] = 3600
REDIS_DB: Final[int] = int(environ.get("REDIS_DB", 14))
REDIS_PORT: Final[int] = int(environ.get("REDIS_PORT", 6379))
REDIS_HOST: Final[str] = environ.get("REDIS_RW_HOST", "localhost")
REDIS_PASSWORD: Final[Optional[str]] = environ.get("REDIS_PASSWORD", None)


class InMemoryStore(Store):
    def __init__(self):
        self.store: Dict[str, str] = {}

    def set(self, key: str, value: str) -> None:
        self.store[key] = value

    def get(self, key: str) -> Optional[str]:
        return self.store.get(key, {})

    def exists(self, key: str) -> bool:
        return key in self.store

    def setex(self, key: str, exp_seconds: int, value: str) -> None:
        self.store[key] = value

    def delete(self, key: str) -> None:
        self.store.pop(key, None)


class RedisStore(Store):
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


def get_sim_store() -> SimulationStore:
    """
    Getting the simulation store based on system configuration
    """
    global sim_store
    if sim_store is None:
        try:
            store = RedisStore(
                host=REDIS_HOST, password=REDIS_PASSWORD, port=REDIS_PORT, db=REDIS_DB
            )
        except Exception as e:
            store = InMemoryStore()
            print(f"Error initializing redis: {e}", flush=True)

        sim_store = SimulationStore(store, experation_seconds=CACHE_EXPERATION_SECONDS)
    return sim_store
