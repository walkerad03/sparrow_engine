from typing import Any, Dict, Type, TypeVar

T = TypeVar("T")


class ResourceManager:
    def __init__(self):
        self._resources: Dict[Type[Any], Any] = {}

    def add(self, resource: Any) -> None:
        self._resources[type(resource)] = resource

    def get(self, resource_type: Type[T]) -> T:
        res = self._resources.get(resource_type)
        if res is None:
            raise KeyError(f"Resource not found: {resource_type.__name__}")
        return res

    def try_get(self, resource_type: Type[T]) -> T | None:
        return self._resources.get(resource_type)
