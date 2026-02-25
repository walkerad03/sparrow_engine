# sparrow/systems/translation.py
import logging

from sparrow.core.components import Transform, Velocity
from sparrow.core.time import SimulationTime
from sparrow.ecs import World

logger = logging.getLogger(name="sparrow.translation")


def translation_system(world: World) -> None:
    sim_time = world.res_get(SimulationTime)
    view = world.query(Transform, Velocity)

    if not sim_time:
        return

    if len(view) > 0:
        view.Transform.pos += view.Velocity.ds * sim_time.fixed_dt
