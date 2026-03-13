# sparrow/spatial/spatial_index.py
import math
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np


@dataclass
class SpatialIndex:
    cell_size: float = 10.0
    cells: dict[int, set[int]] = field(default_factory=lambda: defaultdict(set))

    _HX: int = field(default=73856093, init=False, repr=False)
    _HY: int = field(default=19349663, init=False, repr=False)
    _HZ: int = field(default=83492791, init=False, repr=False)
    _inv_cell_size: float = field(default=0.1, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.cell_size <= 0.0:
            raise ValueError("cell_size must be > 0.0")
        self._inv_cell_size = 1.0 / self.cell_size

    def get_key(self, pos: np.ndarray) -> int:
        gx = math.floor(float(pos[0]) * self._inv_cell_size)
        gy = math.floor(float(pos[1]) * self._inv_cell_size)
        gz = math.floor(float(pos[2]) * self._inv_cell_size)
        return (gx * self._HX) ^ (gy * self._HY) ^ (gz * self._HZ)

    def get_keys(self, positions: np.ndarray) -> np.ndarray:
        if positions.size == 0:
            return np.empty(0, dtype=np.int32)

        grid = np.floor(positions[:, :3] * self._inv_cell_size).astype(
            np.int64,
            copy=False,
        )
        keys = (
            (grid[:, 0] * self._HX)
            ^ (grid[:, 1] * self._HY)
            ^ (grid[:, 2] * self._HZ)
        )
        return keys.astype(np.int32, copy=False)
