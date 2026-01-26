from typing import Any, Dict, List, Type

import numpy as np

from sparrow.types import ArchetypeMask, EntityId


class Archetype:
    def __init__(self, mask: ArchetypeMask, types: List[Type[Any]]):
        self.mask = mask
        self.types = types
        self.entities: List[EntityId] = []

        self.arrays: Dict[Type[Any], np.ndarray] = {}  # For SoA data
        self.objects: Dict[
            Type[Any], List[Any]
        ] = {}  # Fallback for generic objects
        self.capacity = 100
        self.count = 0

        for t in types:
            if hasattr(t, "__soa_dtype__"):
                dtype = getattr(t, "__soa_dtype__")
                self.arrays[t] = np.zeros(self.capacity, dtype=dtype)
            else:
                self.objects[t] = []

    def add(self, eid: EntityId, comp_data: Dict[Type[Any], Any]) -> int:
        """Appends a new entity and its data to the columns."""
        idx = self.count

        if idx >= self.capacity:
            self._resize(self.capacity * 2)

        self.entities.append(eid)

        for t in self.types:
            component = comp_data[t]

            if t in self.arrays:
                field_values = []
                for field_def in t.__soa_dtype__:
                    field_name = field_def[0]
                    val = getattr(component, field_name)

                    if hasattr(val, "__iter__") and not isinstance(
                        val, (str, bytes, list, tuple, np.ndarray)
                    ):
                        val = tuple(val)

                    field_values.append(val)

                self.arrays[t][idx] = tuple(field_values)
            else:
                self.objects[t].append(comp_data[t])

        self.count += 1
        return idx

    def _resize(self, new_cap) -> None:
        self.capacity = new_cap
        for t, arr in self.arrays.items():
            old_arr = arr
            self.arrays[t] = np.zeros(new_cap, dtype=old_arr.dtype)
            self.arrays[t][: self.count] = old_arr[: self.count]

    def remove(self, row_idx: int) -> EntityId:
        """
        Removes an entity via Swap-and-Pop to keep memory contiguous.
        Returns the EntityId of the entity that was moved into the gap.
        """
        last_idx = self.count - 1
        moved_entity = self.entities[last_idx]

        # Case A: Remove the last element. Only pop.
        if row_idx == last_idx:
            self.entities.pop()
            for col in self.objects.values():
                col.pop()
            self.count -= 1
            return EntityId(-1)  # No entity was moved

        # Removing from the middle. Swap last into current.
        self.entities[row_idx] = moved_entity
        self.entities.pop()  # Remove the duplicate at the end

        for col in self.objects.values():
            col[row_idx] = col[-1]
            col.pop()

        for arr in self.arrays.values():
            arr[row_idx] = arr[last_idx]

        self.count -= 1
        return moved_entity
