from sparrow.core.world import World
from sparrow.resources.core import SimulationTime


def simulation_time_system(world: World) -> None:
    if not world.try_resource(SimulationTime):
        world.add_resource(SimulationTime())
