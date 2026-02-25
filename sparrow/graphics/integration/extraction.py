# sparrow/graphics/integration/extraction.py
import numpy as np

from sparrow.core.components import Transform
from sparrow.core.time import SimulationTime
from sparrow.ecs.world import World
from sparrow.graphics.integration.components import (
    Camera,
    DirectionalLight,
    Mesh,
)
from sparrow.graphics.integration.frame import (
    CameraData,
    ObjectInstance,
    RenderFrame,
)
from sparrow.math import create_perspective_projection, create_view_matrix
from sparrow.types import EntityId, Vector3

_FALLBACK_MAT = np.eye(4, dtype="f4")
_FALLBACK_VEC = np.zeros(3, dtype="f4")


def extract_render_frame_system(world: World) -> None:
    """
    System: Queries the ECS and constructs a RenderFrame snapshot.
    """
    sim_time = world.res_get(SimulationTime)

    if not sim_time:
        return

    time_s = sim_time.ticks * sim_time.fixed_dt
    dt = sim_time.fixed_dt

    camera_data = _extract_active_camera(world)
    sun_dir, sun_col = _extract_sun(world)

    objects = []
    transforms = np.empty((0, 4, 4), dtype="f4")

    view = world.query(Transform, Mesh)
    if len(view) > 0:
        m_vis = view.Mesh.visible
        total_visible = int(m_vis.sum())

        if total_visible > 0:
            transforms = np.empty((total_visible, 4, 4), dtype="f4")
            transform_index = 0

            positions = view.Transform.pos
            rotations = view.Transform.rot
            scales = view.Transform.scale

            m_handles = view.Mesh.handle

            eids = view._indices

            for i in range(len(view)):
                if not m_vis[i]:
                    continue

                _write_model_matrix(
                    transforms[transform_index],
                    positions[i],
                    rotations[i],
                    scales[i],
                )

                objects.append(
                    ObjectInstance(
                        entity_id=EntityId(eids[i]),
                        mesh_id=m_handles[i].id,
                        transform_index=transform_index,
                        albedo_id=None,
                        color=(1.0, 0.5, 0.2, 1.0),
                        roughness=0.5,
                        metallic=0.0,
                    )
                )
                transform_index += 1

    frame = RenderFrame(
        camera=camera_data,
        objects=objects,
        transforms=transforms,
        sun_direction=Vector3(sun_dir[0], sun_dir[1], sun_dir[2]),
        sun_color=sun_col,
        time=time_s,
        delta_time=dt,
    )

    world.res_add(frame)


def _write_model_matrix(out: np.ndarray, pos, rot, scale) -> None:
    """Write a 4x4 model matrix into `out` from single PRS."""
    x, y, z, w = rot
    n = (x * x + y * y + z * z + w * w) ** 0.5
    if n == 0.0:
        x = y = z = 0.0
        w = 1.0
    else:
        inv = 1.0 / n
        x *= inv
        y *= inv
        z *= inv
        w *= inv

    xx = x * x
    yy = y * y
    zz = z * z
    xy = x * y
    xz = x * z
    yz = y * z
    wx = w * x
    wy = w * y
    wz = w * z

    sx, sy, sz = scale

    # Row-major 3x3 rotation, scaled by S on the right (column scale)
    out[0, 0] = (1.0 - 2.0 * (yy + zz)) * sx
    out[0, 1] = (2.0 * (xy - wz)) * sy
    out[0, 2] = (2.0 * (xz + wy)) * sz
    out[0, 3] = pos[0]

    out[1, 0] = (2.0 * (xy + wz)) * sx
    out[1, 1] = (1.0 - 2.0 * (xx + zz)) * sy
    out[1, 2] = (2.0 * (yz - wx)) * sz
    out[1, 3] = pos[1]

    out[2, 0] = (2.0 * (xz - wy)) * sx
    out[2, 1] = (2.0 * (yz + wx)) * sy
    out[2, 2] = (1.0 - 2.0 * (xx + yy)) * sz
    out[2, 3] = pos[2]

    out[3, 0] = 0.0
    out[3, 1] = 0.0
    out[3, 2] = 0.0
    out[3, 3] = 1.0


def _extract_active_camera(world: World) -> CameraData:
    view = world.query(Camera, Transform)

    if len(view) > 0:
        actives = view.Camera.active  # numpy array of bools

        for i in range(len(view)):
            if actives[i]:
                # Found active camera
                fov = view.Camera.fov[i]
                near = view.Camera.near[i]
                far = view.Camera.far[i]

                pos = view.Transform.pos[i]
                rot = view.Transform.rot[i]

                aspect = 16.0 / 9.0
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

    # Fallback if no camera exists
    return CameraData(
        _FALLBACK_MAT, _FALLBACK_MAT, _FALLBACK_MAT, _FALLBACK_VEC, 0.1, 100.0
    )


def _extract_sun(world: World):
    view = world.query(DirectionalLight, Transform)

    if len(view) > 0:
        # Just take the first light
        return ((0.5, -0.8, 0.2), view.DirectionalLight.color[0])

    return ((0.5, -0.8, 0.2), (1.0, 1.0, 1.0))
