import math
from dataclasses import replace

import numpy as np

from sparrow.core.components import Camera, Transform
from sparrow.core.world import World
from sparrow.graphics.ecs.frame_submit import CameraData
from sparrow.resources.cameras import CameraOutput


def camera_system(world: World) -> None:
    camera_out = world.try_resource(CameraOutput)
    if camera_out is None:
        return

    new_cam_out = replace(camera_out, active=None)
    world.mutate_resource(new_cam_out)

    for _, camera, transform in world.join(Camera, Transform):
        eye = transform.pos
        ex, ey, ez = eye

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

        new_cam_out = replace(
            camera_out,
            active=CameraData(
                view=view,
                proj=proj,
                view_proj=view_proj,
                position_ws=eye,
                near=camera.near_clip,
                far=camera.far_clip,
            ),
        )
        world.mutate_resource(new_cam_out)
