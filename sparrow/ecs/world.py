# sparrow/ecs/world.py
from __future__ import annotations

import logging
from collections import deque
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

import numpy as np

logger = logging.getLogger("Sparrow.ECS")

T = TypeVar("T")


class World:
    """The central data container for the Sparrow engine.

    Manages the lifecycle of resources, events, and component registries.
    """

    def __init__(self, capacity: int = 1_000_000):
        """Initializes the ECS World with empty storage for all data types."""
        self._resources: Dict[Union[Type, str], Any] = {}
        self._events: Dict[Type, List[Any]] = {}

        self.capacity = capacity
        self._next_entity_id = 0
        self._free_entities: deque[int] = deque()

        self._masks = np.zeros(self.capacity, dtype=np.uint64)

        self._component_registry: Dict[Type, int] = {}
        self._component_dtypes: Dict[Type, np.dtype] = {}
        self._component_arrays: Dict[int, np.ndarray] = {}
        self._next_comp_id: int = 0

    def entity_add(self) -> int:
        """Creates a new entity handle."""
        if self._free_entities:
            return self._free_entities.popleft()

        entity_id = self._next_entity_id
        self._next_entity_id += 1
        return entity_id

    def entity_rem(self, entity_id: int) -> None:
        """Destroys an entity and clears its component mask."""
        self._masks[entity_id] = 0
        self._free_entities.append(entity_id)

    def res_add(
        self,
        resource: Any,
        key: Optional[Union[Type, str]] = None,
    ) -> None:
        """Adds a resource to the world.

        Args:
            resource (Any): The object instance to store.
            key (Optional[Union[Type, str]]): The key to store it under.
                Defaults to the object's type.
        """
        k = key or type(resource)
        self._resources[k] = resource

    def res_set(
        self,
        resource: Any,
        key: Optional[Union[Type, str]] = None,
    ) -> None:
        """Updates an existing resource.

        Args:
            resource (Any): The new object instance.
            key (Optional[Union[Type, str]]): The key to update.

        Raises:
            KeyError: If the resource does not already exist.
        """
        k = key or type(resource)
        if k not in self._resources:
            raise KeyError(f"Resource '{k}' does not exist in the World.")
        self._resources[k] = resource

    def res_get(self, key: Union[Type[T], str]) -> Optional[T]:
        """Fetches a resource from the world.

        Args:
            key (Union[Type[T], str]): The type or string key of the resource.

        Returns:
            Optional[T]: The resource instance or None if not found.
        """
        resource = self._resources.get(key, None)
        if resource is None:
            return None
        return cast(T, resource)

    def res_rem(self, key: Union[Type, str]) -> None:
        """Removes a resource from the world.

        Args:
            key (Union[Type, str]): The key of the resource to remove.
        """
        if key in self._resources:
            del self._resources[key]

    def event_add(self, event: Any) -> None:
        """Publishes an event to the internal bus.

        Args:
            event (Any): The event instance (typically a dataclass).
        """
        event_type = type(event)
        if event_type not in self._events:
            self._events[event_type] = []
        self._events[event_type].append(event)

    def event_get(self, event_type: Type[T]) -> List[T]:
        """Retrieves and clears all events of a specific type.

        This follows a 'drain' pattern: once fetched, the internal buffer
        for that event type is cleared to prevent duplicate processing.

        Args:
            event_type (Type[T]): The class of events to retrieve.

        Returns:
            List[T]: A list of event instances.
        """
        events = self._events.get(event_type, [])
        self._events[event_type] = []
        return events

    def comp_add(self, entity_id: int, *components: Any) -> None:
        """Adds one or more components to an entity.

        Overloaded to accept multiple component instances.
        """
        for comp in components:
            comp_type = type(comp)
            comp_id = self._register_component(comp_type)

            self._masks[entity_id] |= comp_id

            self._write_component_data(entity_id, comp_id, comp)

    def comp_get(self, entity_id: int, component_type: Type[T]) -> Optional[T]:
        """Fetches a component's data for a specific entity.

        Note: Since we are SoA, this creates a temporary object or returns
        the raw record. For performance, use query() instead of comp_get.
        """
        comp_id = self._component_registry.get(component_type)
        if not comp_id or not (self._masks[entity_id] & comp_id):
            return None

        arr = self._component_arrays[comp_id]
        # Return the specific row/record
        return cast(T, arr[entity_id])

    def comp_set(self, entity_id: int, component: Any) -> None:
        """Updates an existing component's data.

        Raises:
            KeyError: If the entity doesn't have this component type.
        """
        comp_type = type(component)
        comp_id = self._component_registry.get(comp_type)

        if not comp_id or not (self._masks[entity_id] & comp_id):
            raise KeyError(
                f"Entity {entity_id} does not have component {comp_type.__name__}"
            )

        self._write_component_data(entity_id, comp_id, component)

    def comp_rem(self, entity_id: int, *component_types: Type) -> None:
        """Removes one or more components from an entity.

        Args:
            entity_id: The entity to modify.
            component_types: The classes of components to remove.
        """
        for c_type in component_types:
            comp_id = self._component_registry.get(c_type)
            if comp_id:
                self._masks[entity_id] &= ~comp_id
                self._component_arrays[comp_id][entity_id] = 0

    def _write_component_data(
        self, entity_id: int, comp_id: int, comp: Any
    ) -> None:
        """Internal helper to map object attributes to the SoA NumPy array.

        This assumes the component object has attributes matching the
        dtype field names of the registered array.
        """
        arr = self._component_arrays[comp_id]

        if arr.dtype.names:
            for name in arr.dtype.names:
                if hasattr(comp, name):
                    arr[name][entity_id] = getattr(comp, name)
        else:
            arr[entity_id] = comp

    def _register_component(self, component_type: Type) -> int:
        """Registers a component type and allocates its SoA buffer.

        Args:
            component_type (Type): The class to register as a component.

        Returns:
            int: The unique bit ID for this component.
        """
        if component_type not in self._component_registry:
            comp_id = 1 << self._next_comp_id
            self._component_registry[component_type] = comp_id
            self._next_comp_id += 1

            dtype = getattr(component_type, "dtype", np.float32)
            self._component_arrays[comp_id] = np.zeros(
                self.capacity, dtype=dtype
            )

        return self._component_registry[component_type]

    def query(self, *component_types: Type) -> QueryView:
        """Finds entity indices that possess all of the requested components.

        This uses vectorized bitwise operations to filter the entity mask array
        extremely efficiently across the entire capacity.

        Args:
            *component_types: The component classes to filter for.

        Returns:
            np.ndarray: An array of entity IDs (indices) that match the query.
        """
        if not component_types:
            indices = np.where(self._masks > 0)[0]
            return QueryView(self, indices)

        required_mask = np.uint64(0)
        for comp_type in component_types:
            comp_id = self._component_registry.get(comp_type)
            if comp_id is None:
                return QueryView(self, np.array([], dtype=np.int64))
            required_mask |= comp_id

        indices = np.where((self._masks & required_mask) == required_mask)[0]

        return QueryView(self, indices)


class ComponentProxy:
    """A proxy for a specific component type across a queried set of entities."""

    def __init__(self, world: "World", indices: np.ndarray, comp_type: Type):
        self._world = world
        self._indices = indices
        self._comp_type = comp_type
        self._comp_id = world._component_registry[comp_type]
        self._array = world._component_arrays[self._comp_id]

    def __getattr__(self, name: str) -> Any:
        """Accesses a field across all entities in the query as a view."""
        # Returns a view of the numpy array for the specific field
        # This allows for things like: view.Transform.pos += 1
        return self._array[name][self._indices]

    def __setattr__(self, name: str, value: Any):
        """Sets a field across all entities in the query."""
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._array[name][self._indices] = value


class QueryView:
    """A collection of proxies for entities matching a specific query."""

    def __init__(self, world: "World", indices: np.ndarray):
        self._world = world
        self._indices = indices
        self._proxies: Dict[Type, ComponentProxy] = {}

    def __getattr__(self, name: str) -> ComponentProxy:
        """Dynamically creates or retrieves a ComponentProxy by class name."""
        # Find the component type by its name string (e.g., "Transform")
        # This enables the 'view.Transform' syntax.
        for comp_type in self._world._component_registry:
            if comp_type.__name__ == name:
                if comp_type not in self._proxies:
                    self._proxies[comp_type] = ComponentProxy(
                        self._world, self._indices, comp_type
                    )
                return self._proxies[comp_type]

        raise AttributeError(f"Component type '{name}' not found in registry.")

    def __len__(self) -> int:
        return len(self._indices)
