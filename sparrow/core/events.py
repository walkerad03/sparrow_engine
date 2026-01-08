from collections import defaultdict
from typing import Any, Dict, List, Type, TypeVar

E = TypeVar("E")


class Event:
    """Base class for all Events."""

    pass


class EventManager:
    def __init__(self):
        self._queues: Dict[Type[Any], List[Any]] = defaultdict(list)

    def emit(self, event: Any) -> None:
        event_type = type(event)
        self._queues[event_type].append(event)

    def get(self, event_type: Type[E]) -> List[E]:
        if event_type in self._queues:
            events = self._queues[event_type]
            self._queues[event_type] = []
            return events
        return []

    def clear_all(self) -> None:
        self._queues.clear()
