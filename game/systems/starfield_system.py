from game.components.player import Player
from game.components.star import Star
from sparrow.core.components import EID, Transform, Velocity
from sparrow.core.world import World
from sparrow.resources.core import SimulationTime
from sparrow.resources.rendering import RenderViewport


def starfield_system(world: World) -> None:
    sim_time = world.try_resource(SimulationTime)
    viewport = world.try_resource(RenderViewport)

    if not (sim_time and viewport):
        return

    dt = sim_time.delta_seconds
    w, h = viewport.width, viewport.height
    buffer = 100.0

    ref_vel_x, ref_vel_y = 0.0, 0.0

    for count, (vels, _) in world.get_batch(Velocity, Player):
        if count > 0:
            v = vels["vec"][0]
            ref_vel_x, ref_vel_y = v[0], v[1]

    if ref_vel_x == 0 and ref_vel_y == 0:
        return

    for count, (transforms, _, eids) in world.get_batch(Transform, Star, EID):
        pos_x = transforms["pos"][:, 0]
        pos_y = transforms["pos"][:, 1]

        depths = transforms["scale"][:, 0]

        shift_x = ref_vel_x * depths * 5.0 * dt
        shift_y = ref_vel_y * depths * 5.0 * dt

        pos_x -= shift_x
        pos_y -= shift_y

        min_x, min_y = -buffer, -buffer
        span_x, span_y = w + (buffer * 2), h + (buffer * 2)

        pos_x[:] = ((pos_x - min_x) % span_x) + min_x
        pos_y[:] = ((pos_y - min_y) % span_y) + min_y
