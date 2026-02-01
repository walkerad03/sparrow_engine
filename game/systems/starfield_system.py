from game.components.player import Player
from game.components.star import Star
from sparrow.core.components import Transform, Velocity
from sparrow.core.query import Query
from sparrow.core.world import World
from sparrow.resources.cameras import CameraOutput
from sparrow.resources.core import SimulationTime
from sparrow.types import Vector2


def starfield_system(world: World) -> None:
    sim_time = world.try_resource(SimulationTime)
    cam_out = world.try_resource(CameraOutput)

    if not (sim_time and cam_out and cam_out.active):
        return

    dt = sim_time.delta_seconds

    player_pos = Vector2(0, 0)
    player_vel = Vector2(0, 0)

    found_player = False
    for _, (trans, vels, _) in Query(world, Transform, Velocity, Player):
        player_pos = Vector2(trans.pos.x[0], trans.pos.y[0])
        player_vel = Vector2(vels.vec.x[0], vels.vec.y[0])
        found_player = True
        break

    if not found_player:
        return

    proj = cam_out.active.proj
    world_h = 2.0 / proj[1, 1] if proj[1, 1] > 0 else 1000.0
    world_w = 2.0 / proj[0, 0] if proj[0, 0] > 0 else 1000.0

    buffer = 200.0
    span_x = world_w + buffer
    span_y = world_h + buffer

    half_span_x = span_x * 0.5
    half_span_y = span_y * 0.5

    for count, (transforms, _) in Query(world, Transform, Star):
        depths = transforms.scale.x

        shift_x = player_vel.x * depths * 0.1 * dt
        shift_y = player_vel.y * depths * 0.1 * dt

        transforms.pos.x -= shift_x
        transforms.pos.y -= shift_y

        dist_x = transforms.pos.x - player_pos.x
        dist_y = transforms.pos.y - player_pos.y

        wrapped_dist_x = ((dist_x + half_span_x) % span_x) - half_span_x
        wrapped_dist_y = ((dist_y + half_span_y) % span_y) - half_span_y

        transforms.pos.x[:] = player_pos.x + wrapped_dist_x
        transforms.pos.y[:] = player_pos.y + wrapped_dist_y
