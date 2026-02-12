# sparrow/systems/camera.py
import math
from dataclasses import replace

import numpy as np

from sparrow.core.components import EID, Camera2D, Transform
from sparrow.core.world import World
from sparrow.graphics.integration.components import Camera
from sparrow.graphics.integration.frame import CameraData
from sparrow.resources.cameras import CameraOutput


def camera_system(world: World) -> None:
    camera_out = world.resource_get(CameraOutput)
    if not camera_out:
        camera_out = CameraOutput()
        world.resource_add(camera_out)

    new_cam_data = None

    for count, (cams, transforms, eids) in world.query(Camera, Transform, EID):
        eid = eids.id[0]

        new_cam_data = _calculate_camera_3d(
            world.component_get(eid, Camera, exception_on_fail=True),
            world.component_get(eid, Transform, exception_on_fail=True),
        )
        break

    if new_cam_data is None:
        for count, (camera_2d, transforms, eids) in world.query(
            Camera2D, Transform, EID
        ):
            eid = eids.id[0]
            new_cam_data = _calculate_camera_2d(
                world.component_get(eid, Camera2D, exception_on_fail=True),
                world.component_get(eid, Transform, exception_on_fail=True),
            )
            break

    if new_cam_data:
        world.resource_set(replace(camera_out, active=new_cam_data))


def _calculate_camera_3d(camera: Camera, transform: Transform) -> CameraData:
    ex, ey, ez = transform.pos

    tx, ty, tz = camera.target

    fx, fy, fz = tx - ex, ty - ey, tz - ez
    len_f = math.sqrt(fx * fx + fy * fy + fz * fz)
    inv_len_f = 1.0 / len_f if len_f > 1e-9 else 1.0
    fx, fy, fz = fx * inv_len_f, fy * inv_len_f, fz * inv_len_f

    sx, sy, sz = -fz, 0.0, fx
    len_s_sq = sx * sx + sz * sz
    if len_s_sq < 1e-12:
        sx, sy, sz = 1.0, 0.0, 0.0
    else:
        inv_len_s = 1.0 / math.sqrt(len_s_sq)
        sx, sy, sz = sx * inv_len_s, sy * inv_len_s, sz * inv_len_s

    ux = sy * fz - sz * fy
    uy = sz * fx - sx * fz
    uz = sx * fy - sy * fx

    trans_s = -(sx * ex + sy * ey + sz * ez)
    trans_u = -(ux * ex + uy * ey + uz * ez)
    trans_f = fx * ex + fy * ey + fz * ez

    view = np.array(
        [
            [sx, sy, sz, trans_s],
            [ux, uy, uz, trans_u],
            [-fx, -fy, -fz, trans_f],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )

    aspect = camera.aspect_ratio
    tan_half_fov = math.tan(math.radians(camera.fov) * 0.5)
    fl = 1.0 / tan_half_fov

    p00 = fl / aspect
    p11 = fl

    inv_nf = 1.0 / (camera.near_clip - camera.far_clip)
    p22 = (camera.far_clip + camera.near_clip) * inv_nf
    p23 = (2.0 * camera.far_clip * camera.near_clip) * inv_nf

    proj = np.array(
        [
            [p00, 0.0, 0.0, 0.0],
            [0.0, p11, 0.0, 0.0],
            [0.0, 0.0, p22, p23],
            [0.0, 0.0, -1.0, 0.0],
        ],
        dtype=np.float64,
    )

    view_proj = np.array(
        [
            [p00 * sx, p00 * sy, p00 * sz, p00 * trans_s],
            [p11 * ux, p11 * uy, p11 * uz, p11 * trans_u],
            [p22 * -fx, p22 * -fy, p22 * -fz, p22 * trans_f + p23],
            [fx, fy, fz, -trans_f],
        ],
        dtype=np.float64,
    )

    pos_ws = np.array(transform.pos, dtype=np.float64)

    return CameraData(
        view=view,
        proj=proj,
        view_proj=view_proj,
        position=pos_ws,
        near=camera.near_clip,
        far=camera.far_clip,
    )


def _calculate_camera_2d(camera: Camera2D, transform: Transform) -> CameraData:
    aspect = camera.aspect_ratio

    top = camera.zoom * 0.5
    right = top * aspect

    ex, ey, ez = transform.pos

    view = np.array(
        [
            [1.0, 0.0, 0.0, -ex],
            [0.0, 1.0, 0.0, -ey],
            [0.0, 0.0, 1.0, -ez],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )

    inv_r = 1.0 / right
    inv_t = 1.0 / top
    inv_fn = 1.0 / (camera.far_clip - camera.near_clip)

    p22 = -2.0 * inv_fn
    p23 = -(camera.far_clip + camera.near_clip) * inv_fn

    proj = np.array(
        [
            [inv_r, 0.0, 0.0, 0.0],
            [0.0, inv_t, 0.0, 0.0],
            [0.0, 0.0, p22, p23],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )

    view_proj = np.array(
        [
            [inv_r, 0.0, 0.0, -ex * inv_r],
            [0.0, inv_t, 0.0, -ey * inv_t],
            [0.0, 0.0, p22, p23],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )

    pos_ws = np.array(transform.pos, dtype=np.float64)

    return CameraData(
        view=view,
        proj=proj,
        view_proj=view_proj,
        position=pos_ws,
        near=camera.near_clip,
        far=camera.far_clip,
    )
