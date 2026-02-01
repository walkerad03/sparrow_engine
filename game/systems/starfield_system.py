from game.components.player import Player
from game.components.star import Star
from sparrow.core.components import Transform, Velocity
from sparrow.core.query import Query
from sparrow.core.world import World
from sparrow.resources.core import SimulationTime
from sparrow.resources.rendering import RenderViewport
from sparrow.types import Vector2


def starfield_system(world: World) -> None:
    sim_time = world.try_resource(SimulationTime)
    viewport = world.try_resource(RenderViewport)

    if not (sim_time and viewport):
        return

    dt = sim_time.delta_seconds
    w, h = viewport.width, viewport.height
    buffer = 100.0

    ref_vel = Vector2(0, 0)
    for count, (vels, _) in Query(world, Velocity, Player):
        ref_vel = Vector2(vels.vec.x[0], vels.vec.y[0])
        break

    if ref_vel.x == 0 and ref_vel.y == 0:
        return

    for count, (transforms, _) in Query(world, Transform, Star):
        depths = transforms.scale.x

        shift_x = ref_vel.x * depths * 0.5 * dt
        shift_y = ref_vel.y * depths * 0.5 * dt

        transforms.pos.x -= shift_x
        transforms.pos.y -= shift_y

        min_x, min_y = -buffer, -buffer
        span_x, span_y = w + (buffer * 2), h + (buffer * 2)

        transforms.pos.x[:] = ((transforms.pos.x - min_x) % span_x) + min_x
        transforms.pos.y[:] = ((transforms.pos.y - min_y) % span_y) + min_y
