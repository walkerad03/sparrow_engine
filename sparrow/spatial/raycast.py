import math
from typing import Optional, Tuple

from .grid import Grid


def raycast(
    grid: Grid, start: Tuple[float, float], end: Tuple[float, float]
) -> Optional[Tuple[float, float]]:
    """
    Casts a ray against the Grid.
    Returns the (x, y) hit position in World Space, or None if no wall was hit.
    """
    x1, y1 = start
    x2, y2 = end

    # 1. Map Coordinates
    map_x = int(x1 // grid.tile_size)
    map_y = int(y1 // grid.tile_size)

    # 2. Delta Dist (Distance ray travels to cross one grid line)
    dx = x2 - x1
    dy = y2 - y1

    # Avoid division by zero
    delta_dist_x = abs(1.0 / dx) if dx != 0 else float("inf")
    delta_dist_y = abs(1.0 / dy) if dy != 0 else float("inf")

    # 3. Step Direction & Initial Side Dist
    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1

    if dx > 0:
        side_dist_x = ((map_x + 1) * grid.tile_size - x1) * delta_dist_x
    else:
        side_dist_x = (x1 - map_x * grid.tile_size) * delta_dist_x

    if dy > 0:
        side_dist_y = ((map_y + 1) * grid.tile_size - y1) * delta_dist_y
    else:
        side_dist_y = (y1 - map_y * grid.tile_size) * delta_dist_y

    # 4. Total Ray Length
    ray_len = math.sqrt(dx * dx + dy * dy)

    # 5. DDA Loop
    hit = False
    max_steps = 100  # Safety break

    # We track total distance traveled to ensure we don't overshoot 'end'
    # Actually, DDA traverses grid cells. We can check if we passed the target grid cell.
    end_map_x = int(x2 // grid.tile_size)
    end_map_y = int(y2 // grid.tile_size)

    while max_steps > 0:
        # Check if we hit a wall
        if grid.get(map_x, map_y) > 0:
            hit = True
            break

        # Check if we reached the end point tile without hitting anything
        if map_x == end_map_x and map_y == end_map_y:
            break

        # Move to next square
        if side_dist_x < side_dist_y:
            side_dist_x += delta_dist_x
            map_x += step_x
        else:
            side_dist_y += delta_dist_y
            map_y += step_y

        max_steps -= 1

    if hit:
        # Calculate intersection point (Roughly)
        # For exact precision, we can use the side_dist values, but
        # usually getting the tile center or edge is enough.
        # Here we return the center of the hit tile.
        return grid.grid_to_world(map_x, map_y)

    return None
