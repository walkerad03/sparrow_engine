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
        eid = int(eids[i])
        new_key = grid.get_key(positions[i])
        old_key = int(old_keys[i])

        if new_key != old_key:
            if old_key in grid.cells:
                grid.cells[old_key].discard(eid)

            grid.cells[new_key].add(eid)

            view.Transform._array["_grid_key"][eids[i]] = new_key
