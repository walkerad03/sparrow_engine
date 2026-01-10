from sparrow.core.components import ChildOf, Transform
from sparrow.core.world import World


def hierarchy_system(world: World) -> None:
    # Query for all entities that have a Transform and are Children
    for child_eid, child_trans, relation in world.join(Transform, ChildOf):
        assert isinstance(child_trans, Transform) and isinstance(relation, ChildOf)
        # 1. Try to get the Parent's Transform
        parent_trans = world.component(relation.parent, Transform)

        # 2. Logic
        if parent_trans:
            new_x = parent_trans.x + relation.offset_x
            new_y = parent_trans.y + relation.offset_y

            new_trans = Transform(new_x, new_y, child_trans.rotation, child_trans.scale)
            world.mutate_component(child_eid, new_trans)

        else:
            # Edge Case: Parent died/deleted.
            # Option A: Delete child?
            # Option B: Remove ChildOf component (detach)?
            # Option C: Do nothing (orphan stays at last known spot).
            pass
