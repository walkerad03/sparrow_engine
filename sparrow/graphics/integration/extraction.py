# sparrow/graphics/integration/extraction.py
# TODO: Get correct transforms
import numpy as np

from sparrow.core.components import EID, Transform
from sparrow.core.query import Query
from sparrow.core.world import World
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
from sparrow.resources.core import SimulationTime


def extract_render_frame_system(world: World) -> None:
    """
    System: Queries the ECS and constructs a RenderFrame snapshot.
    """
    sim_time = world.resource_get(SimulationTime)

    if not sim_time:
        return

    time_s = sim_time.elapsed_seconds
    dt = sim_time.delta_seconds
    camera_data = _extract_active_camera(world)
    sun_dir, sun_col = _extract_sun(world)
    objects = []
    total_visible = 0

    for count, (trans_view, mesh_view, eids_view) in Query(
        world, Transform, Mesh, EID
    ):
        m_vis = mesh_view.visible
        if count > 0:
            total_visible += int(m_vis[:count].sum())

    transforms = np.empty((total_visible, 4, 4), dtype="f4")
    transform_index = 0

    for count, (trans_view, mesh_view, eids_view) in Query(
        world, Transform, Mesh, EID
    ):
        positions = trans_view.pos  # (N, 3)
        rotations = trans_view.rot  # (N, 4)
        scales = trans_view.scale

        m_handles = mesh_view.handle
        m_vis = mesh_view.visible
        eids = eids_view.id

        for i in range(count):
            if not m_vis[i]:
                continue

            # Compute Transform in-place
            _write_model_matrix(
                transforms[transform_index],
                positions[i],
                rotations[i],
                scales[i],
            )

            objects.append(
                ObjectInstance(
                    entity_id=eids[i],
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
        sun_direction=sun_dir,
        sun_color=sun_col,
        time=time_s,
        delta_time=dt,
    )
    world.resource_add(frame)


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
    # Query yields batches, but we just want the first active camera
    for count, (cam_view, trans_view) in Query(world, Camera, Transform):
        actives = cam_view.active  # numpy array of bools

        for i in range(count):
            if actives[i]:
                # Found active camera
                fov = cam_view.fov[i]
                near = cam_view.near[i]
                far = cam_view.far[i]

                pos = trans_view.pos[i]
                rot = trans_view.rot[i]

                aspect = 16.0 / 9.0
                proj = create_perspective_projection(fov, aspect, near, far)
                view = create_view_matrix(pos, rot)

                return CameraData(
                    view=view,
                    proj=proj,
                    view_proj=proj @ view,
                    position=pos,
                    near=near,
                    far=far,
                )

    # Fallback
    return CameraData(np.eye(4), np.eye(4), np.eye(4), np.zeros(3), 0.1, 100.0)


def _extract_sun(world: World):
    # Just take the first light
    for count, (light_view, trans_view) in Query(
        world, DirectionalLight, Transform
    ):
        if count > 0:
            return ((0.5, -0.8, 0.2), light_view.color[0])
    return ((0.5, -0.8, 0.2), (1.0, 1.0, 1.0))
