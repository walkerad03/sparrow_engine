import random
from typing import Tuple

import numpy as np

from game.constants import TILE_SIZE
from sparrow.spatial.grid import Grid

# Define Tile IDs here (or import from constants)
TILE_FLOOR = 0
TILE_WALL = 1
TILE_WATER = 2
TILE_GOLD = 3


def find_spawn_point(grid: Grid) -> Tuple[int, int]:
    """
    Finds a valid TILE_FLOOR coordinate (Grid Space).
    Returns (grid_x, grid_y).
    """
    width, height = grid.width, grid.height

    # 1. Try Random Spots (for variety)
    for _ in range(50):
        rx = random.randint(1, width - 2)
        ry = random.randint(1, height - 2)
        if grid.get(rx, ry) == TILE_FLOOR:
            return rx, ry

    # 2. Fallback: Linear Scan (guaranteed to find something)
    for x in range(1, width - 1):
        for y in range(1, height - 1):
            if grid.get(x, y) == TILE_FLOOR:
                return x, y

    # 3. Emergency: Middle of map (might be a wall, but better than crashing)
    return width // 2, height // 2


def generate_dungeon(width: int, height: int, tile_size: int = TILE_SIZE) -> Grid:
    """
    Game-specific logic to generate a cave system with multiple tile types.
    """
    grid = Grid(width, height, tile_size)

    # 1. Initialize with Random Noise (Walls vs Floors)
    # Using int8 allows values from -128 to 127
    map_data = np.full((width, height), TILE_WALL, dtype=np.int8)

    # Random floor carving
    fill_percent = 45
    for x in range(1, width - 1):
        for y in range(1, height - 1):
            if random.randint(0, 100) > fill_percent:
                map_data[x, y] = TILE_FLOOR

    # 2. Cellular Automata Smoothing (Standard Cave Logic)
    for _ in range(5):
        map_data = _smooth_map(map_data, width, height)

    # 3. Game Specific Decoration Pass
    # Example: Turn isolated walls into Gold, or pools into Water
    for x in range(1, width - 1):
        for y in range(1, height - 1):
            if map_data[x, y] == TILE_FLOOR:
                # 10% chance for a floor to be water
                if random.random() < 0.10:
                    map_data[x, y] = TILE_WATER
            elif map_data[x, y] == TILE_WALL:
                # 5% chance for a wall to be a Gold Vein
                if random.random() < 0.05:
                    map_data[x, y] = TILE_GOLD

    # 4. Write to Grid
    # We access the raw buffer directly for speed
    grid._data = map_data
    return grid


def _smooth_map(old_map, width, height):
    new_map = np.copy(old_map)
    for x in range(1, width - 1):
        for y in range(1, height - 1):
            walls = _count_walls(old_map, x, y)
            if walls > 4:
                new_map[x, y] = TILE_WALL
            elif walls < 4:
                new_map[x, y] = TILE_FLOOR
    return new_map


def _count_walls(m, x, y):
    count = 0
    for i in range(x - 1, x + 2):
        for j in range(y - 1, y + 2):
            if i != x or j != y:
                # Treat anything that isn't a simple floor as a "solid" for smoothing
                if m[i, j] != TILE_FLOOR:
                    count += 1
    return count
