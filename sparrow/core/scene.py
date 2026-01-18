from __future__ import annotations

import math
from typing import TYPE_CHECKING, List

import numpy as np
from numpy.typing import NDArray

from sparrow.core.components import Camera, Mesh, Transform
from sparrow.core.world import World
from sparrow.graphics.ecs.frame_submit import CameraData, DrawItem, RenderFrameInput
from sparrow.types import EntityId

if TYPE_CHECKING:
    from sparrow.core.application import Application


def get_view_matrix(
    eye: NDArray[np.float32], target: NDArray[np.float32]
) -> NDArray[np.float32]:
    """
    Constructs a View Matrix using the optimized scalar math from your snippet.
    """
    ex, ey, ez = float(eye[0]), float(eye[1]), float(eye[2])
    tx, ty, tz = float(target[0]), float(target[1]), float(target[2])

    # Forward (f = target - eye)
    fx, fy, fz = tx - ex, ty - ey, tz - ez
    len_f = math.sqrt(fx * fx + fy * fy + fz * fz)
    inv_len_f = 1.0 / len_f if len_f > 1e-9 else 1.0
    fx, fy, fz = fx * inv_len_f, fy * inv_len_f, fz * inv_len_f

    # Right (s = cross(f, up(0,1,0))) -> (-fz, 0, fx)
    sx, sy, sz = -fz, 0.0, fx
    len_s_sq = sx * sx + sz * sz
    if len_s_sq < 1e-12:
        sx, sy, sz = 1.0, 0.0, 0.0
    else:
        inv_len_s = 1.0 / math.sqrt(len_s_sq)
        sx, sy, sz = sx * inv_len_s, sy * inv_len_s, sz * inv_len_s

    # Up (u = cross(s, f))
    ux = sy * fz - sz * fy
    uy = sz * fx - sx * fz
    uz = sx * fy - sy * fx

    # Translation
    trans_s = -(sx * ex + sy * ey + sz * ez)
    trans_u = -(ux * ex + uy * ey + uz * ez)
    trans_f = fx * ex + fy * ey + fz * ez

    return np.array(
        [
            [sx, sy, sz, trans_s],
            [ux, uy, uz, trans_u],
            [-fx, -fy, -fz, trans_f],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )


def get_data(world: World, eid: EntityId) -> CameraData:
    """
    Returns the full CameraData struct.
    Performs the optimized sparse matrix multiplication (Proj * View) manually
    to avoid the overhead of np.matmul.
    """
    for _, camera, transform in world.join(Camera, Transform):
        eye = transform.pos
        target = camera.target

        # 1. Unpack Scalars
        ex, ey, ez = float(eye[0]), float(eye[1]), float(eye[2])
        tx, ty, tz = float(target[0]), float(target[1]), float(target[2])

        # 2. View Vectors
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

        # 3. Projection Scalars
        aspect = camera.aspect_ratio
        tan_half_fov = math.tan(math.radians(camera.fov) * 0.5)
        fl = 1.0 / tan_half_fov

        # Note: Pre-calculate p00/p11 for the optimized mult below
        p00 = fl / aspect
        p11 = fl

        inv_nf = 1.0 / (camera.near_clip - camera.far_clip)
        p22 = (camera.far_clip + camera.near_clip) * inv_nf
        p23 = (2.0 * camera.far_clip * camera.near_clip) * inv_nf

        # 4. Construct Matrices
        view = np.array(
            [
                [sx, sy, sz, trans_s],
                [ux, uy, uz, trans_u],
                [-fx, -fy, -fz, trans_f],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        )

        proj = np.array(
            [
                [p00, 0.0, 0.0, 0.0],
                [0.0, p11, 0.0, 0.0],
                [0.0, 0.0, p22, p23],
                [0.0, 0.0, -1.0, 0.0],
            ],
            dtype=np.float32,
        )

        # 5. Optimized View-Projection Multiply
        # Since Proj is diagonal-ish, we manually compute the result rows
        vp = np.array(
            [
                [p00 * sx, p00 * sy, p00 * sz, p00 * trans_s],
                [p11 * ux, p11 * uy, p11 * uz, p11 * trans_u],
                [p22 * -fx, p22 * -fy, p22 * -fz, p22 * trans_f + p23],
                [fx, fy, fz, -trans_f],  # This is -1 * ViewRow2
            ],
            dtype=np.float32,
        )

        return CameraData(
            view=view,
            proj=proj,
            view_proj=vp,
            position_ws=eye,
            near=camera.near_clip,
            far=camera.far_clip,
        )

    raise Exception


class Scene:
    def __init__(self, app: Application):
        self.world = World()
        self.camera_entity: EntityId | None = None

        self.app = app

        self.frame_index = 0
        self.last_time = 0

    def on_start(self) -> None:
        """Called when the scene is first activated."""
        pass

    def on_update(self, dt: float) -> None:
        """Called every frame to update game logic."""
        self.frame_index += 1

        # TODO: Poll input, window events, resize handling.
        # If resized, update renderer settings and rebuild graph or trigger resize path.

    def on_exit(self) -> None:
        """Called when transitioning away from this scene."""
        pass

    def get_render_frame(self) -> RenderFrameInput:
        """
        Extracts data from the ECS World to build the FrameContext for the Renderer.
        You can override this if you need custom render logic.
        """
        w, h = self.app.screen_size

        for eid, camera, transform in self.world.join(Camera, Transform):
            cam_data = get_data(self.world, eid)

        draws: List[DrawItem] = []
        draw_id = 0
        for eid, mesh, transform in self.world.join(Mesh, Transform):
            draws.append(
                DrawItem(
                    mesh.mesh_id,
                    mesh.material_id,
                    transform.matrix_transform,
                    draw_id,
                )
            )
            draw_id += 1

        return RenderFrameInput(
            frame_index=self.frame_index,
            dt_seconds=1 / 60,
            camera=cam_data,
            draws=draws,
            point_lights=[],
            viewport_width=w,
            viewport_height=h,
        )
