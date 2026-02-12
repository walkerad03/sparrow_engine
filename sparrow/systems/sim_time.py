from sparrow.core.world import World
from sparrow.resources.core import SimulationTime


def simulation_time_system(world: World) -> None:
    if not world.resource_get(SimulationTime):
        world.resource_add(SimulationTime())
