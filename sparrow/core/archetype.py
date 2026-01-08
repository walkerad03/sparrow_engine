from typing import Any, Dict, List, Type

from sparrow.types import ArchetypeMask, EntityId


class Archetype:
    def __init__(self, mask: ArchetypeMask, types: List[Type[Any]]):
        self.mask = mask
        self.types = types
        # Columnar storage: { Position: [Pos1, Pos2], Velocity: [Vel1, Vel2] }
        self.components: Dict[Type[Any], List[Any]] = {t: [] for t in types}
        self.entities: List[EntityId] = []

    def add(self, eid: EntityId, comp_data: Dict[Type[Any], Any]) -> int:
        """Appends a new entity and its data to the columns."""
        row_idx = len(self.entities)
        self.entities.append(eid)
        for t in self.types:
            self.components[t].append(comp_data[t])
        return row_idx

    def remove(self, row_idx: int) -> EntityId:
        """
        Removes an entity via Swap-and-Pop to keep memory contiguous.
        Returns the EntityId of the entity that was moved into the gap.
        """
        last_idx = len(self.entities) - 1

        # Case A: Remove the last element. Only pop.
        if row_idx == last_idx:
            self.entities.pop()
            for col in self.components.values():
                col.pop()
            return EntityId(-1)  # No entity was moved

        # Removing from the middle. Swap last into current.
        moved_entity = self.entities[last_idx]
        self.entities[row_idx] = moved_entity
        self.entities.pop()  # Remove the duplicate at the end

        for t, col in self.components.items():
            col[row_idx] = col[-1]
            col.pop()

        return moved_entity
