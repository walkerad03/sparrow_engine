from __future__ import annotations

from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    TypeVarTuple,
    Unpack,
)

import numpy as np

from sparrow.core.archetype import Archetype
from sparrow.core.events import EventManager
from sparrow.core.registry import ComponentRegistry
from sparrow.core.resources import ResourceManager
from sparrow.types import ArchetypeMask, EntityId, Quaternion, Vector2, Vector3

T = TypeVar("T")
Ev = TypeVar("Ev")
Ts = TypeVarTuple("Ts")
Cs = TypeVarTuple("Cs")  # variadic component types for join()


class EntityRecord:
    __slots__ = ("archetype", "row")

    def __init__(self, archetype: Archetype, row: int):
        self.archetype = archetype
        self.row = row


class World:
    def __init__(self) -> None:
        self._next_id: int = 1

        # ECS data
        self._archetypes: Dict[int, Archetype] = {}
        self._entities: Dict[EntityId, EntityRecord] = {}

        # Managers
        self._resource_manager = ResourceManager()
        self._event_manager = EventManager()

        # Initialize the "Empty" archetype (Mask 0)
        self._get_or_create_archetype(ArchetypeMask(0), [])

    # RESOURCE MANAGEMENT
    def add_resource(self, resource: Any) -> None:
        """Register a global resource (e.g. Time, Input, Config)."""
        self._resource_manager.add(resource)

    def get_resource(self, resource_type: Type[T]) -> T:
        """Retrieve a resource. Raises KeyError if missing."""
        return self._resource_manager.get(resource_type)

    def try_resource(self, resource_type: Type[T]) -> T | None:
        """Retrieve a resource or returns None."""
        return self._resource_manager.try_get(resource_type)

    def mutate_resource(self, resource_type: Any) -> None:
        """Update an EXISTING resource with a new instance."""
        res_type = type(resource_type)

        if self._resource_manager.try_get(res_type) is None:
            raise KeyError(
                f"Resource {res_type.__name__} does not exist. "
                "Use world.add_resource() to initialize global state."
            )

        self._resource_manager.add(resource_type)

    # EVENT MANAGEMENT
    def emit_event(self, event: Any) -> None:
        """Queues an event signal."""
        self._event_manager.emit(event)

    def get_events(self, event_type: Type[Ev]) -> List[Ev]:
        """Consumes and returns all events of the given type."""
        return self._event_manager.get(event_type)

    # ENTITY MANAGEMENT

    def create_entity(self, *components: Any) -> EntityId:
        """Creates an entity, optionally with starting components."""
        eid = EntityId(self._next_id)
        self._next_id += 1

        arch = self._archetypes[ArchetypeMask(0)]
        row = arch.add(eid, {})
        self._entities[eid] = EntityRecord(arch, row)

        for c in components:
            self.add_component(eid, c)

        return eid

    def add_entity(self, eid: EntityId, *components: Any) -> None:
        """
        Manually spawns an entity with a specific ID.
        Useful for networking (replicating server IDs) or loading saves.
        """
        if eid >= self._next_id:
            self._next_id = eid + 1

        if eid in self._entities:
            for c in components:
                self.add_component(eid, c)
            return

        arch = self._archetypes[ArchetypeMask(0)]
        row = arch.add(eid, {})
        self._entities[eid] = EntityRecord(arch, row)

        for c in components:
            self.add_component(eid, c)

    def delete_entity(self, eid: EntityId) -> None:
        if eid not in self._entities:
            return

        record = self._entities[eid]
        moved_eid = record.archetype.remove(record.row)

        if moved_eid != -1:
            self._entities[moved_eid].row = record.row

        del self._entities[eid]

    # COMPONENT MANAGEMENT
    def add_component(self, eid: EntityId, component: object) -> None:
        record = self._entities[eid]
        old_arch = record.archetype
        comp_type = type(component)
        comp_mask = ComponentRegistry.get_mask(comp_type)

        if old_arch.mask & comp_mask:
            self.mutate_component(eid, component)
            return

        new_mask = ArchetypeMask(old_arch.mask | comp_mask)
        self._move_entity(eid, record, new_mask, add_component=component)

    def remove_component(
        self, eid: EntityId, component_type: Type[Any]
    ) -> None:
        record = self._entities.get(eid)
        if not record:
            return

        old_arch = record.archetype
        comp_mask = ComponentRegistry.get_mask(component_type)

        # If component is not present, do nothing
        if not (old_arch.mask & comp_mask):
            return

        # Move to new archetype (current mask MINUS component mask)
        new_mask = ArchetypeMask(old_arch.mask & ~comp_mask)
        self._move_entity(eid, record, new_mask, remove_type=component_type)

    def mutate_component(self, eid: EntityId, component: Any) -> None:
        """
        Update an EXISTING component with a new instance.
        """
        record = self._entities.get(eid)
        if not record:
            raise KeyError(f"Entity {eid} does not exist.")

        comp_type = type(component)
        arch = record.archetype

        if comp_type in arch.arrays:
            field_values = []
            for field_def in comp_type.__soa_dtype__:
                field_name = field_def[0]
                val = getattr(component, field_name)

                if hasattr(val, "__iter__") and not isinstance(
                    val, (str, bytes, list, tuple, np.ndarray)
                ):
                    val = tuple(val)
                field_values.append(val)

            arch.arrays[comp_type][record.row] = tuple(field_values)

        elif comp_type in arch.objects:
            arch.objects[comp_type][record.row] = component

        else:
            raise KeyError(
                f"Entity {eid} cannot mutate {comp_type.__name__}: Component missing. "
                "Use world.add() to attach new components."
            )

    def component(self, eid: EntityId, component_type: Type[T]) -> Optional[T]:
        record = self._entities.get(eid)
        if not record:
            return None

        arch = record.archetype
        row = record.row

        if component_type in arch.arrays:
            raw_data = arch.arrays[component_type][row]
            return self._reconstruct_component(component_type, raw_data)

        if component_type in arch.objects:
            return arch.objects[component_type][row]

        return None

    def has(self, eid: EntityId, component_type: Type[Any]) -> bool:
        record = self._entities.get(eid)
        if not record:
            return False
        mask = ComponentRegistry.get_mask(component_type)
        return bool(record.archetype.mask & mask)

    # QUERIES
    def join(
        self,
        *component_types: Unpack[Tuple[Type[Cs], ...]],
    ) -> Iterator[Tuple[EntityId, *Cs]]:
        """
        Legacy Query.
        Slower than get_batch() because it reconstructs objects from arrays.
        """
        query_mask = 0
        for t in component_types:
            query_mask |= ComponentRegistry.get_mask(t)

        for arch in self._archetypes.values():
            if (arch.mask & query_mask) == query_mask:
                # Iterate rows
                for i, eid in enumerate(arch.entities):
                    components = []
                    for t in component_types:
                        if t in arch.arrays:
                            # Reconstruct from SoA
                            raw = arch.arrays[t][i]
                            comp = self._reconstruct_component(t, raw)
                            components.append(comp)
                        else:
                            # Get from AoS
                            components.append(arch.objects[t][i])

                    yield (eid, *components)

    def get_batch(
        self,
        *component_types: Unpack[Tuple[Type[Cs], ...]],
    ) -> Iterator[Tuple[EntityId, *Cs]]:
        """
        High-performance query. Yields SoA arrays directly.
        Returns: (count, [Array_Comp1, Array_Comp2, ...])
        """
        query_mask = 0
        for t in component_types:
            query_mask |= ComponentRegistry.get_mask(t)

        for arch in self._archetypes.values():
            if (arch.mask & query_mask) == query_mask:
                if arch.count > 0:
                    arrays = []
                    for t in component_types:
                        if t in arch.arrays:
                            arrays.append(arch.arrays[t][: arch.count])
                        else:
                            arrays.append(arch.objects[t][: arch.count])

                    yield (arch.count, arrays)

    # INTERNAL HELPERS

    def _get_or_create_archetype(
        self, mask: ArchetypeMask, types: List[Type[Any]]
    ) -> Archetype:
        if mask not in self._archetypes:
            self._archetypes[mask] = Archetype(mask, types)
        return self._archetypes[mask]

    def _move_entity(
        self,
        eid: EntityId,
        record: EntityRecord,
        new_mask: ArchetypeMask,
        add_component: Any = None,
        remove_type: Type[Any] | None = None,
    ) -> None:
        """Handles the logic of moving an entity between tables"""
        old_arch = record.archetype

        # 1. Collect data for the new archetype
        data = {}
        for t in old_arch.types:
            if t != remove_type:
                if t in old_arch.arrays:
                    raw = old_arch.arrays[t][record.row]
                    data[t] = self._reconstruct_component(t, raw)
                else:
                    data[t] = old_arch.objects[t][record.row]

        if add_component:
            data[type(add_component)] = add_component

        # 2. Get new archetype
        new_types = list(data.keys())
        new_arch = self._get_or_create_archetype(new_mask, new_types)

        # 3. Remove from old
        moved_eid = old_arch.remove(record.row)
        if moved_eid != -1:
            self._entities[moved_eid].row = record.row

        # 4. Add to new
        new_row = new_arch.add(eid, data)
        self._entities[eid] = EntityRecord(new_arch, new_row)

    def _reconstruct_component(self, comp_type: Type[T], raw_data: Any) -> T:
        """
        Re-inflates a Dataclass component from a Numpy void record.
        """
        kwargs = {}
        # Iterate the dtypes to know which fields to extract
        for field_def in comp_type.__soa_dtype__:
            name = field_def[0]
            val = raw_data[name]
            shape = field_def[2] if len(field_def) > 2 else ()

            # Simple heuristic to reconstruct Vector types
            # (Requires Vector3/Quaternion to accept unpacked args in __init__)
            if len(shape) > 0:
                if shape == (3,) and (
                    "pos" in name
                    or "vel" in name
                    or "scale" in name
                    or "size" in name
                    or "center" in name
                ):
                    val = Vector3(*val)
                elif shape == (4,) and "rot" in name:
                    val = Quaternion(*val)
                elif shape == (2,):
                    val = Vector2(*val)
                elif shape == (1,):
                    val = val[0]

            kwargs[name] = val

        return comp_type(**kwargs)
