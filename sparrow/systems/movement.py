from sparrow.core.components import EID, Transform, Velocity
from sparrow.core.world import World
from sparrow.resources.core import SimulationTime


def movement_system(world: World) -> None:
    sim_time = world.try_resource(SimulationTime)
    if not sim_time:
        return

    dt = sim_time.delta_seconds

    for count, (transforms, vels, eids) in world.get_batch(
        Transform, Velocity, EID
    ):
        transforms["pos"][:, 0] += vels["vec"][:, 0] * dt
        transforms["pos"][:, 1] += vels["vec"][:, 1] * dt
