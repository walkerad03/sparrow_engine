# sparrow/systems/sim_time.py
from sparrow.core.time import SimulationTime
from sparrow.ecs.world import World
from sparrow.runtime.timing import FixedStep


def simulation_time_system(world: World) -> None:
    time_res = world.res_get(SimulationTime)
    fixed_step = world.res_get(FixedStep)

    if not fixed_step:
        return

    if not time_res:
        time_res = SimulationTime(fixed_dt=fixed_step.dt)
        world.res_add(time_res)

    time_res.ticks += 1
