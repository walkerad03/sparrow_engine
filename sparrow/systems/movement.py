from sparrow.core.components import Transform, Velocity
from sparrow.core.world import World
from sparrow.resources.core import SimulationTime


def movement_system(world: World) -> None:
    sim_time = world.resource_get(SimulationTime)
    if not sim_time:
        return

    dt = sim_time.delta_seconds

    for count, (trans, vel) in world.query(Transform, Velocity):
        trans.pos += vel.vec * dt
