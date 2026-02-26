import numpy as np

from sparrow.core.components import Transform
from sparrow.ecs.world import World
from sparrow.graphics.integration.components import Camera
from sparrow.graphics.integration.frame import CameraData, CameraOutput
from sparrow.math import create_perspective_projection, create_view_matrix
from sparrow.runtime.managers import InterfaceManager


def camera_prepare_system(world: World) -> None:
    """Compute active camera matrices and publish them for rendering."""
    camera_data = _extract_active_camera(world)
    world.res_add(CameraOutput(active=camera_data))


def _extract_active_camera(world: World) -> CameraData:
    view = world.query(Camera, Transform)

    if len(view) == 0:
        return _fallback_camera_data()

    aspect = _resolve_aspect_ratio(world)
    active = view.Camera.active

    for i in range(len(view)):
        if not active[i]:
            continue

        fov = float(view.Camera.fov[i])
        near = float(view.Camera.near[i])
        far = float(view.Camera.far[i])

        pos = np.array(view.Transform.pos[i], dtype="f4")
        rot = view.Transform.rot[i]

        proj = create_perspective_projection(fov, aspect, near, far)
        view_mat = create_view_matrix(pos, rot)

        return CameraData(
            view=view_mat,
            proj=proj,
            view_proj=proj @ view_mat,
            position=pos,
            near=near,
            far=far,
        )

    return _fallback_camera_data()


def _resolve_aspect_ratio(world: World) -> float:
    interface = world.res_get(InterfaceManager)
    if not interface:
        return 16.0 / 9.0

    width, height = interface.wnd.buffer_size
    if height <= 0:
        return 16.0 / 9.0

    return float(width) / float(height)


def _fallback_camera_data() -> CameraData:
    mat = np.eye(4, dtype="f4")
    pos = np.zeros(3, dtype="f4")
    return CameraData(
        view=mat,
        proj=mat,
        view_proj=mat,
        position=pos,
        near=0.1,
        far=100.0,
    )
