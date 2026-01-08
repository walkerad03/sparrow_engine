from typing import Tuple

import numpy as np


class Grid:
    def __init__(self, width: int, height: int, tile_size: int = 16):
        self.width = width
        self.height = height
        self.tile_size = tile_size

        # 0 = Empty, 1 = Wall, 2 = Glass, etc.
        # Int8 is enough for 127 tile types.
        self._data = np.zeros((width, height), dtype=np.int8)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x: int, y: int) -> int:
        if not self.in_bounds(x, y):
            return 1  # Out of bounds is treated as a Wall
        return self._data[x, y]

    def set(self, x: int, y: int, value: int):
        if self.in_bounds(x, y):
            self._data[x, y] = value

    def world_to_grid(self, wx: float, wy: float) -> Tuple[int, int]:
        """Converts pixel coordinates to grid indices."""
        return int(wx // self.tile_size), int(wy // self.tile_size)

    def grid_to_world(self, gx: int, gy: int) -> Tuple[float, float]:
        """Returns the CENTER of the tile in pixel coordinates."""
        return (gx * self.tile_size) + (self.tile_size / 2), (gy * self.tile_size) + (
            self.tile_size / 2
        )
