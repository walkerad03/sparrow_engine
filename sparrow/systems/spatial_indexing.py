from sparrow.core import Transform
from sparrow.ecs import World
from sparrow.spatial.spatial_index import SpatialIndex


def spatial_indexing_system(world: World) -> None:
    grid = world.res_get(SpatialIndex)

    if grid is None:
        grid = SpatialIndex()
        world.res_add(grid)

    view = world.query(Transform)

    if len(view) == 0:
        return

    positions = view.Transform.pos
    old_keys = view.Transform._grid_key
    eids = view._indices

    new_keys = grid.get_keys(positions)
    changed_mask = new_keys != old_keys

    if not changed_mask.any():
        return

    changed_eids = eids[changed_mask]
    changed_old = old_keys[changed_mask]
    changed_new = new_keys[changed_mask]
    cells = grid.cells

    for eid, old_key, new_key in zip(
        changed_eids.tolist(),
        changed_old.tolist(),
        changed_new.tolist(),
    ):
        old_bucket = cells.get(old_key)
        if old_bucket is not None:
            old_bucket.discard(eid)
        cells[new_key].add(eid)

    view.Transform._array["_grid_key"][changed_eids] = changed_new
