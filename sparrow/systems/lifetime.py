from dataclasses import replace

import numpy as np

from sparrow.core.components import EID, Lifetime
from sparrow.core.world import World
from sparrow.resources.core import SimulationTime, ToDelete


def lifetime_system(world: World) -> None:
    to_del = world.try_resource(ToDelete)
    if not to_del:
        to_del = ToDelete()
        world.add_resource(to_del)

    st = world.try_resource(SimulationTime)
    if not st:
        return

    for count, (lts, eids) in world.get_batch(Lifetime, EID):
        lts["time_alive"] += st.delta_seconds

        expired_mask = (lts["time_alive"] >= lts["duration"]).flatten()

        if np.any(expired_mask):
            ids_to_remove = ids_to_remove = eids["id"][expired_mask]

            new_to_del = replace(
                to_del, entities=to_del.entities.update(ids_to_remove)
            )
            world.mutate_resource(new_to_del)

    if to_del.entities:
        for eid in to_del.entities:
            world.delete_entity(eid)
        world.mutate_resource(ToDelete())
