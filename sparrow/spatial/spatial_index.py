# sparrow/spatial/spatial_index.py
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np


@dataclass
class SpatialIndex:
    cell_size: float = 10.0
    cells: dict[int, list[int]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def get_key(self, pos: np.ndarray) -> int:
        gx, gy, gz = np.floor(pos / self.cell_size).astype(int)

        return (gx * 73856093) ^ (gy * 19349663) ^ (gz * 83492791)
