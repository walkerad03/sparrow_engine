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
from sparrow.types import Quaternion


def extract_render_frame_system(world: World) -> None:
    """
    System: Queries the ECS and constructs a RenderFrame snapshot.
    """
    sim_time = world.try_resource(SimulationTime)

    if not sim_time:
        return

    time_s = sim_time.elapsed_seconds
    dt = sim_time.delta_seconds
    camera_data = _extract_active_camera(world)
    sun_dir, sun_col = _extract_sun(world)
    objects = []

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

            # Compute Transform
            model_mat = _compute_model_matrix_single(
                positions[i], rotations[i], scales[i]
            )

            objects.append(
                ObjectInstance(
                    entity_id=eids[i],
                    mesh_id=m_handles[i].id,
                    transform=model_mat,
                    albedo_id=None,
                    color=(1.0, 0.5, 0.2, 1.0),
                    roughness=0.5,
                    metallic=0.0,
                )
            )

        frame = RenderFrame(
            camera=camera_data,
            objects=objects,
            sun_direction=sun_dir,
            sun_color=sun_col,
            time=time_s,
            delta_time=dt,
        )
        world.add_resource(frame)


def _compute_model_matrix_single(pos, rot, scale) -> np.ndarray:
    """Helper to build 4x4 matrix from single PRS."""
    T = np.eye(4, dtype="f4")
    T[:3, 3] = pos

    R = Quaternion(*rot).to_matrix4()
    S = np.diag([scale[0], scale[1], scale[2], 1.0]).astype("f4")

    return T @ R @ S


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
