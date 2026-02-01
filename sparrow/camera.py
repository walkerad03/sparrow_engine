from sparrow.core.components import Camera2D, Transform
from sparrow.types import Vector2


def screen_to_world_cam2d(
    screen_norm: Vector2, camera: Camera2D, camera_trans: Transform
) -> Vector2:
    view_height = camera.zoom
    view_width = view_height * camera.aspect_ratio

    dx = (screen_norm.x - 0.5) * view_width
    dy = (0.5 - screen_norm.y) * view_height

    return Vector2(camera_trans.pos.x + dx, camera_trans.pos.y + dy)
