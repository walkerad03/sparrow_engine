from sparrow.core import Transform
from sparrow.ecs import World
from sparrow.spatial.spatial_index import SpatialIndex


def spatial_indexing_system(world: World) -> None:
    grid = world.res_get(SpatialIndex)

    if not grid:
        grid = SpatialIndex()
        world.res_add(grid)

    view = world.query(Transform)

    if len(view) == 0:
        return

    positions = view.Transform.pos
    old_keys = view.Transform._grid_key
    eids = view._indices

    for i in range(len(view)):
        new_key = grid.get_key(positions[i])

        if new_key != old_keys[i]:
            if old_keys[i] in grid.cells:
                grid.cells[old_keys[i]].remove(eids[i])

            grid.cells[new_key].append(eids[i])

            view.Transform._array["_grid_key"][eids[i]] = new_key
