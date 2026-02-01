from dataclasses import replace

from game.components.player import Player
from game.components.star import Star
from sparrow.core.components import Transform, Velocity
from sparrow.core.world import World
from sparrow.resources.core import SimulationTime
from sparrow.resources.rendering import RenderViewport
from sparrow.types import Vector2, Vector3


def starfield_system(world: World) -> None:
    sim_time = world.try_resource(SimulationTime)
    viewport = world.try_resource(RenderViewport)

    if not (sim_time and viewport):
        return

    dt = sim_time.delta_seconds
    w, h = viewport.width, viewport.height
    buffer = 100

    ref_vel = Vector2(0.0, 0.0)

    for _, vel, _ in world.join(Velocity, Player):
        ref_vel = vel.vec
        break

    if ref_vel.x == 0 and ref_vel.y == 0:
        return

    for eid, t, _ in world.join(Transform, Star):
        depth = t.scale.x

        parallax_speed = ref_vel * depth * 5 * dt

        sx = t.pos.x - parallax_speed.x
        sy = t.pos.y - parallax_speed.y

        if sx < -buffer:
            sx += w + (buffer * 2)
        elif sx > w + buffer:
            sx -= w + (buffer * 2)

        if sy < -buffer:
            sy += h + (buffer * 2)
        elif sy > h + buffer:
            sy -= h + (buffer * 2)

        world.add_component(eid, replace(t, pos=Vector3(sx, sy, 0)))
