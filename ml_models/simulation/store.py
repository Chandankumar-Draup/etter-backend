from abc import ABC, abstractmethod
from typing import TypedDict, List, Dict, Any, cast, Optional
import json


class SimulationRequestData(TypedDict):
    n_iterations: int
    roles: List[Dict]
    company: str
    automation_factor: float


class Store(ABC):
    """
    Abstract base class for storing simulation data
    """

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    def setex(self, key: str, exp_seconds: int, value: str) -> None:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass


class SimulationStore:
    def __init__(self, store: Store, experation_seconds: int = 3600):
        self._store = store
        self._experation_seconds = experation_seconds

    def create(self, sim_cache_key: str, **kwargs):
        sim_data = {}
        for key, value in kwargs.items():
            sim_data[key] = value

        self._store.setex(
            sim_cache_key,
            self._experation_seconds,
            json.dumps(sim_data),
        )

    def update(self, sim_cache_key: str, **kwargs):
        sim_data = self.get(sim_cache_key)
        if sim_data is None:
            sim_data = {}
        for key, value in kwargs.items():
            sim_data[key] = value
        self._store.setex(sim_cache_key, self._experation_seconds, json.dumps(sim_data))

    def get(self, sim_cache_key: str) -> Optional[Dict]:
        data = self._store.get(sim_cache_key)
        if data:
            simulation_data = cast(Dict[str, Any], json.loads(data))
            return simulation_data

    def exists(self, sim_cache_key: str) -> bool:
        return self.get(sim_cache_key) is not None

    def delete(self, sim_cache_key: str) -> None:
        self._store.delete(sim_cache_key)
