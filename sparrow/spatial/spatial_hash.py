from collections import defaultdict
from typing import Dict, List, Set, Tuple

from ..types import EntityId, Rect


class SpatialHash:
    def __init__(self, cell_size: int = 64):
        self.cell_size = cell_size
        # Map: (cell_x, cell_y) -> List of EntityIds
        self.buckets: Dict[Tuple[int, int], Set[EntityId]] = defaultdict(set)
        # Reverse lookup to handle moves efficiently
        self._entity_cells: Dict[EntityId, Set[Tuple[int, int]]] = defaultdict(set)

    def _get_cells(self, rect: Rect) -> List[Tuple[int, int]]:
        """Returns all buckets that a rectangle overlaps."""
        x, y, w, h = rect

        start_x = int(x // self.cell_size)
        end_x = int((x + w) // self.cell_size)
        start_y = int(y // self.cell_size)
        end_y = int((y + h) // self.cell_size)

        cells = []
        for cx in range(start_x, end_x + 1):
            for cy in range(start_y, end_y + 1):
                cells.append((cx, cy))
        return cells

    def insert(self, eid: EntityId, rect: Rect):
        """Add or Update an entity in the hash."""
        self.remove(eid)  # Clear old position first

        cells = self._get_cells(rect)
        for cell in cells:
            self.buckets[cell].add(eid)
            self._entity_cells[eid].add(cell)

    def remove(self, eid: EntityId):
        """Removes an entity from all its buckets."""
        if eid in self._entity_cells:
            for cell in self._entity_cells[eid]:
                if cell in self.buckets:
                    self.buckets[cell].discard(eid)
                    if not self.buckets[cell]:
                        del self.buckets[cell]  # Cleanup empty buckets
            del self._entity_cells[eid]

    def query(self, rect: Rect) -> Set[EntityId]:
        """Returns unique entities in the buckets overlapping the rect."""
        results = set()
        for cell in self._get_cells(rect):
            if cell in self.buckets:
                results.update(self.buckets[cell])
        return results

    def clear(self):
        self.buckets.clear()
        self._entity_cells.clear()
