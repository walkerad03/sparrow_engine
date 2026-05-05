# sparrow/graphics/integration/extraction.py
import numpy as np

from sparrow.core.components import Transform
from sparrow.core.time import SimulationTime
from sparrow.ecs.world import World
from sparrow.graphics.integration.components import (
    DirectionalLight,
    Material,
    Mesh,
)
from sparrow.graphics.integration.frame import (
    CameraData,
    CameraOutput,
    RenderFrame,
)
from sparrow.types import Vector3

_FALLBACK_MAT = np.eye(4, dtype="f4")
_FALLBACK_VEC = np.zeros(3, dtype="f4")
_DEFAULT_BASE_COLOR = (1.0, 1.0, 1.0, 1.0)
_DEFAULT_ROUGHNESS = 0.5
_DEFAULT_METALLIC = 0.0
_DEFAULT_EMISSIVE = 0.0


def extract_render_frame_system(world: World) -> None:
    """
    System: Queries the ECS and constructs a RenderFrame snapshot.
    """
    sim_time = world.res_get(SimulationTime)

    if not sim_time:
        return

    time_s = sim_time.ticks * sim_time.fixed_dt
    dt = sim_time.fixed_dt

    camera_data = _extract_prepared_camera(world)
    sun_dir, sun_col = _extract_sun(world)

    objects = []
    transforms = np.empty((0, 4, 4), dtype="f4")
    mesh_ids = np.empty(0, dtype=np.int64)
    albedo_ids = np.empty(0, dtype=np.int64)
    colors = np.empty((0, 4), dtype="f4")
    roughness = np.empty(0, dtype="f4")
    metallic = np.empty(0, dtype="f4")
    emissive = np.empty(0, dtype="f4")

    view = world.query(Transform, Mesh)
    if len(view) > 0:
        m_vis = view.Mesh.visible
        visible_indices = np.flatnonzero(m_vis)
        total_visible = int(visible_indices.size)

        if total_visible > 0:
            positions = view.Transform.pos
            rotations = view.Transform.rot
            scales = view.Transform.scale
            m_ids = view.Mesh.mesh_id
            eids = view._indices

            vis_pos = positions[visible_indices]
            vis_rot = rotations[visible_indices]
            vis_scale = scales[visible_indices]
            vis_eids = eids[visible_indices]

            transforms = _write_model_matrices(vis_pos, vis_rot, vis_scale)
            # Keep old field for compatibility; new hot path uses columnar fields.
            objects = []

            mesh_ids = m_ids[visible_indices].astype(np.int64, copy=False)
            albedo_ids = np.full(total_visible, -1, dtype=np.int64)
            colors = np.empty((total_visible, 4), dtype="f4")
            colors[:, :] = _DEFAULT_BASE_COLOR
            roughness = np.full(total_visible, _DEFAULT_ROUGHNESS, dtype="f4")
            metallic = np.full(total_visible, _DEFAULT_METALLIC, dtype="f4")
            emissive = np.full(total_visible, _DEFAULT_EMISSIVE, dtype="f4")

            mat_comp_id = world._component_registry.get(Material)
            if mat_comp_id is not None:
                mat_mask = np.uint64(mat_comp_id)
                has_material = (world._masks[vis_eids] & mat_mask) == mat_mask

                if has_material.any():
                    slots = np.flatnonzero(has_material)
                    rows = world._component_arrays[mat_comp_id][
                        vis_eids[has_material]
                    ]
                    colors[slots] = rows["base_color"]
                    roughness[slots] = rows["roughness"]
                    metallic[slots] = rows["metallic"]
                    emissive[slots] = rows["emissive"]

                    albedo_col = rows["albedo"]
                    # Fast path: current ECS layout stores albedo as float4, not handles.
                    # In that case, keep default -1 and avoid per-item Python work.
                    if albedo_col.dtype == np.object_:
                        for slot, handle in zip(slots, albedo_col):
                            if handle is not None:
                                albedo_ids[slot] = handle.id

    frame = RenderFrame(
        camera=camera_data,
        objects=objects,
        transforms=transforms,
        mesh_ids=mesh_ids,
        albedo_ids=albedo_ids,
        colors=colors,
        roughness=roughness,
        metallic=metallic,
        emissive=emissive,
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


def _write_model_matrices(
    positions: np.ndarray,
    rotations: np.ndarray,
    scales: np.ndarray,
) -> np.ndarray:
    count = positions.shape[0]
    out = np.zeros((count, 4, 4), dtype="f4")
    if count == 0:
        return out

    x = rotations[:, 0]
    y = rotations[:, 1]
    z = rotations[:, 2]
    w = rotations[:, 3]

    n = np.sqrt(x * x + y * y + z * z + w * w)
    safe = n > 0.0
    inv = np.zeros_like(n)
    inv[safe] = 1.0 / n[safe]

    x = np.where(safe, x * inv, 0.0)
    y = np.where(safe, y * inv, 0.0)
    z = np.where(safe, z * inv, 0.0)
    w = np.where(safe, w * inv, 1.0)

    xx = x * x
    yy = y * y
    zz = z * z
    xy = x * y
    xz = x * z
    yz = y * z
    wx = w * x
    wy = w * y
    wz = w * z

    sx = scales[:, 0]
    sy = scales[:, 1]
    sz = scales[:, 2]

    out[:, 0, 0] = (1.0 - 2.0 * (yy + zz)) * sx
    out[:, 0, 1] = (2.0 * (xy - wz)) * sy
    out[:, 0, 2] = (2.0 * (xz + wy)) * sz
    out[:, 0, 3] = positions[:, 0]

    out[:, 1, 0] = (2.0 * (xy + wz)) * sx
    out[:, 1, 1] = (1.0 - 2.0 * (xx + zz)) * sy
    out[:, 1, 2] = (2.0 * (yz - wx)) * sz
    out[:, 1, 3] = positions[:, 1]

    out[:, 2, 0] = (2.0 * (xz - wy)) * sx
    out[:, 2, 1] = (2.0 * (yz + wx)) * sy
    out[:, 2, 2] = (1.0 - 2.0 * (xx + yy)) * sz
    out[:, 2, 3] = positions[:, 2]

    out[:, 3, 3] = 1.0
    return out


def _extract_prepared_camera(world: World) -> CameraData:
    camera_out = world.res_get(CameraOutput)
    if camera_out:
        return camera_out.active

    # Fallback when camera prep has not yet populated the resource
    return CameraData(
        _FALLBACK_MAT, _FALLBACK_MAT, _FALLBACK_MAT, _FALLBACK_VEC, 0.1, 100.0
    )


def _extract_sun(world: World):
    view = world.query(DirectionalLight, Transform)

    if len(view) > 0:
        # Calculate forward vector from the light's rotation
        rot = view.Transform.rot[0]

        # v' = v + 2 * q_vec x (q_vec x v + q_w * v)
        v = np.array([0, 0, -1], dtype="f4")
        q_vec = np.array([rot[0], rot[1], rot[2]], dtype="f4")
        q_w = rot[3]
        uv = np.cross(q_vec, v)
        uuv = np.cross(q_vec, uv)
        forward = v + 2 * (q_w * uv + uuv)

        intensity = view.DirectionalLight.intensity[0]
        color = view.DirectionalLight.color[0]
        final_color = (
            color[0] * intensity,
            color[1] * intensity,
            color[2] * intensity,
        )

        return (tuple(forward), final_color)

    return ((0.5, -0.8, 0.2), (1.0, 1.0, 1.0))
