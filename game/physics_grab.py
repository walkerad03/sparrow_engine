from dataclasses import dataclass

# Import your existing freecam state and math helpers
from game.freecam import (
    FreeCamState,
    _find_active_camera_index,
    _forward_vector,
)
from sparrow.core import Transform
from sparrow.ecs.world import World
from sparrow.graphics.integration.components import Camera
from sparrow.input.resources import InputState
from sparrow.physics.server import PhysicsServer
from sparrow.types import Vector3


@dataclass
class GrabState:
    is_grabbing: bool = False
    body_id: int = -1
    constraint_id: int = -1
    hold_distance: float = 0.0


def physics_grab_system(world: World) -> None:
    physics = world.res_get(PhysicsServer)
    input_state = world.res_get(InputState)
    cam_state = world.res_get(FreeCamState)

    if physics is None or input_state is None or cam_state is None:
        return

    # Ensure GrabState exists in the world
    grab_state = world.res_get(GrabState)
    if not grab_state:
        grab_state = GrabState()
        world.res_add(grab_state)

    # 1. Query the active camera's position
    view = world.query(Camera, Transform)
    if len(view) == 0:
        return

    cam_index = _find_active_camera_index(view.Camera.active)
    if cam_index < 0:
        return

    cam_pos_array = view.Transform.pos[cam_index]
    cam_pos = Vector3(
        float(cam_pos_array[0]),
        float(cam_pos_array[1]),
        float(cam_pos_array[2]),
    )

    # 2. Derive the forward direction using the camera's yaw and pitch
    cam_forward_array = _forward_vector(cam_state.yaw, cam_state.pitch)
    cam_forward = Vector3(
        float(cam_forward_array[0]),
        float(cam_forward_array[1]),
        float(cam_forward_array[2]),
    )

    is_clicking = input_state.is_action_pressed("mouse_right_click")

    # 3. Raycast and Constraint Logic
    if is_clicking and not grab_state.is_grabbing:
        ray_end = Vector3(
            cam_pos.x + (cam_forward.x * 50.0),
            cam_pos.y + (cam_forward.y * 50.0),
            cam_pos.z + (cam_forward.z * 50.0),
        )

        hit = physics.raycast(cam_pos, ray_end)

        if hit and physics.get_mass(hit.body_id) > 0.0:
            dx = hit.hit_pos.x - cam_pos.x
            dy = hit.hit_pos.y - cam_pos.y
            dz = hit.hit_pos.z - cam_pos.z
            grab_state.hold_distance = (dx**2 + dy**2 + dz**2) ** 0.5

            grab_state.constraint_id = physics.create_world_tether(
                hit.body_id, hit.hit_pos, max_force=150.0, erp=0.03
            )
            grab_state.is_grabbing = True
            grab_state.body_id = hit.body_id

    elif is_clicking and grab_state.is_grabbing:
        target_pos = Vector3(
            cam_pos.x + (cam_forward.x * grab_state.hold_distance),
            cam_pos.y + (cam_forward.y * grab_state.hold_distance),
            cam_pos.z + (cam_forward.z * grab_state.hold_distance),
        )
        physics.update_world_tether(grab_state.constraint_id, target_pos)

    elif not is_clicking and grab_state.is_grabbing:
        physics.remove_tether(grab_state.constraint_id)
        grab_state.is_grabbing = False
        grab_state.body_id = -1
        grab_state.constraint_id = -1
