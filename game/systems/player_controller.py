import math
from dataclasses import replace

import numpy as np

from game.components.player import Player
from game.factories.game_object import create_bullet, create_spaceship_trail
from sparrow.core.components import Transform, Velocity
from sparrow.core.world import World
from sparrow.input.handler import InputHandler
from sparrow.math import magnitude_vec, norm_vec, rotate_vec2
from sparrow.resources.cameras import CameraOutput
from sparrow.resources.core import SimulationTime
from sparrow.types import Quaternion, Vector2


def player_controller_system(world: World) -> None:
    inp = world.try_resource(InputHandler)
    sim_time = world.try_resource(SimulationTime)
    cam = world.try_resource(CameraOutput)

    if not (inp and sim_time and cam):
        return

    dt = sim_time.delta_seconds
    cam_data = cam.active

    if not cam_data:
        return

    mx, my = inp.get_mouse_position()

    ndc_x = (mx * 2.0) - 1.0
    ndc_y = (my * 2.0) - 1.0

    ndc_vec = np.array([ndc_x, ndc_y, 0.0, 1.0], dtype=np.float64)

    inv_view_proj = np.linalg.inv(cam_data.view_proj)

    world_pos_homo = inv_view_proj @ ndc_vec

    if world_pos_homo[3] != 0:
        world_pos_homo /= world_pos_homo[3]

    mouse_pos_world = Vector2(world_pos_homo[0], world_pos_homo[1])

    trail_requests = []
    bullet_requests = []

    for eid, trans, vel_comp, _ in world.join(Transform, Velocity, Player):
        # --- INPUT & PHYSICS ---
        current_vel = vel_comp.vec
        pos_2d = Vector2(trans.pos.x, trans.pos.y)

        mouse_diff = pos_2d - mouse_pos_world

        # Thrust
        mag = magnitude_vec(mouse_diff)
        norm_diff = norm_vec(mouse_diff) if mag > 0 else Vector2(0, 0)
        norm_diff_vec2 = Vector2(norm_diff.x, norm_diff.y)

        # Physics Constants
        force_scalar = 3600.0
        drag_scalar = 0.003

        if inp.get_mouse_pressed()[2]:
            force_scalar *= 4
        if inp.is_pressed("SPACE"):
            force_scalar *= 0
            drag_scalar *= 0
        force_vec = norm_diff_vec2 * max(-(mag**2), -force_scalar)
        current_vel += force_vec * dt

        # Drag
        speed = magnitude_vec(current_vel)
        if speed > 0:
            drag_dir = norm_vec(current_vel)
            drag_dir_vec2 = Vector2(drag_dir.x, drag_dir.y)
            drag_force = drag_dir_vec2 * (speed**2) * drag_scalar
            current_vel -= drag_force * dt

        # Rotation
        angle = math.atan2(mouse_diff.y, mouse_diff.x)
        new_rot = Quaternion.from_euler(0.0, angle + (math.pi / 2), 0.0)

        # Apply Updates
        world.add_component(eid, replace(trans, rot=new_rot))
        world.add_component(eid, Velocity(current_vel))

        # --- SPAWN TRAILS ---
        off_l = Vector2(-4.5, -5.5)
        off_r = Vector2(4.5, -5.5)
        rot_angle = angle + (math.pi / 2)

        # Calculate engine positions
        trail_offset = current_vel * dt
        engine_l_curr = pos_2d + rotate_vec2(off_l, rot_angle)
        engine_r_curr = pos_2d + rotate_vec2(off_r, rot_angle)

        trail_requests.append((engine_l_curr - trail_offset, engine_l_curr))
        trail_requests.append((engine_r_curr - trail_offset, engine_r_curr))

        if inp.get_mouse_pressed()[0]:
            bullet_requests.append((pos_2d, angle))

    for pos_a, pos_b in trail_requests:
        create_spaceship_trail(world, pos_a=pos_a, pos_b=pos_b)

    for pos, ang in bullet_requests:
        create_bullet(world, pos=pos, speed=900, angle=ang)
