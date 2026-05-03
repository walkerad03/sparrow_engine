import math
from dataclasses import dataclass

import numpy as np

from sparrow.core import Transform
from sparrow.core.time import SimulationTime
from sparrow.ecs import World
from sparrow.graphics.integration import Camera
from sparrow.input.events import MouseMoveEvent
from sparrow.input.resources import InputState
from sparrow.types import Quaternion


@dataclass
class FreeCamConfig:
    move_speed: float = 10.0
    look_sensitivity: float = 0.0025  # radians per pixel
    max_pitch_radians: float = math.radians(89.0)


@dataclass
class FreeCamState:
    initialized: bool = False
    yaw: float = 0.0
    pitch: float = 0.0


def freecam_system(world: World) -> None:
    input_state = world.res_get(InputState)
    if not input_state:
        return

    sim_time = world.res_get(SimulationTime)
    dt = sim_time.fixed_dt if sim_time else (1.0 / 60.0)

    config = world.res_get(FreeCamConfig)
    if not config:
        config = FreeCamConfig()
        world.res_add(config)

    state = world.res_get(FreeCamState)
    if not state:
        state = FreeCamState()
        world.res_add(state)

    view = world.query(Camera, Transform)
    if len(view) == 0:
        return

    cam_index = _find_active_camera_index(view.Camera.active)
    if cam_index < 0:
        return

    rot = view.Transform.rot
    pos = view.Transform.pos

    if not state.initialized:
        state.yaw, state.pitch = _yaw_pitch_from_quaternion(rot[cam_index])
        state.initialized = True

    dx = 0.0
    dy = 0.0
    for event in world.event_get(MouseMoveEvent):
        dx += float(event.dx)
        dy += float(event.dy)

    if dx != 0.0 or dy != 0.0:
        state.yaw -= dx * config.look_sensitivity
        state.pitch -= dy * config.look_sensitivity
        state.pitch = max(
            -config.max_pitch_radians,
            min(config.max_pitch_radians, state.pitch),
        )

    q = _quaternion_from_yaw_pitch(state.yaw, state.pitch)
    rot[cam_index] = (q.x, q.y, q.z, q.w)
    view.Transform.rot = rot

    forward = _forward_vector(state.yaw, state.pitch)
    right = _right_vector(state.yaw)
    up = _up_vector(state.yaw, state.pitch)

    wish = np.zeros(3, dtype="f4")

    if input_state.is_action_pressed("move_forward"):
        wish += forward
    if input_state.is_action_pressed("move_backward"):
        wish -= forward
    if input_state.is_action_pressed("move_right"):
        wish += right
    if input_state.is_action_pressed("move_left"):
        wish -= right
    if input_state.is_action_pressed("move_up"):
        wish += up
    if input_state.is_action_pressed("move_down"):
        wish -= up

    norm = float(np.linalg.norm(wish))
    if norm > 0.0:
        wish *= (config.move_speed * dt) / norm
        pos[cam_index] = pos[cam_index] + wish
        view.Transform.pos = pos


def _find_active_camera_index(active_flags: np.ndarray) -> int:
    for i in range(len(active_flags)):
        if active_flags[i]:
            return i
    return -1


def _quaternion_from_yaw_pitch(yaw: float, pitch: float) -> Quaternion:
    sy = math.sin(yaw * 0.5)
    cy = math.cos(yaw * 0.5)
    sx = math.sin(pitch * 0.5)
    cx = math.cos(pitch * 0.5)

    # q = q_yaw * q_pitch
    return Quaternion(
        x=cy * sx,
        y=sy * cx,
        z=-sy * sx,
        w=cy * cx,
    )


def _yaw_pitch_from_quaternion(rot: np.ndarray) -> tuple[float, float]:
    x = float(rot[0])
    y = float(rot[1])
    z = float(rot[2])
    w = float(rot[3])

    n = math.sqrt(x * x + y * y + z * z + w * w)
    if n <= 1e-8:
        return 0.0, 0.0

    inv = 1.0 / n
    x *= inv
    y *= inv
    z *= inv
    w *= inv

    r02 = 2.0 * (x * z + w * y)
    r12 = 2.0 * (y * z - w * x)
    r22 = 1.0 - 2.0 * (x * x + y * y)

    fx = -r02
    fy = -r12
    fz = -r22

    pitch = math.asin(max(-1.0, min(1.0, fy)))
    yaw = math.atan2(-fx, -fz)
    return yaw, pitch


def _forward_vector(yaw: float, pitch: float) -> np.ndarray:
    cp = math.cos(pitch)
    return np.array(
        [
            -math.sin(yaw) * cp,
            math.sin(pitch),
            -math.cos(yaw) * cp,
        ],
        dtype="f4",
    )


def _right_vector(yaw: float) -> np.ndarray:
    return np.array(
        [
            math.cos(yaw),
            0.0,
            -math.sin(yaw),
        ],
        dtype="f4",
    )


def _up_vector(yaw: float, pitch: float) -> np.ndarray:
    return np.array(
        [
            math.sin(yaw) * math.sin(pitch),
            math.cos(pitch),
            math.cos(yaw) * math.sin(pitch),
        ],
        dtype="f4",
    )
