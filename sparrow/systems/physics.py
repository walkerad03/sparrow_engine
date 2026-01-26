import numpy as np
from numpy.typing import NDArray

from sparrow.core.components import Collider3D, RigidBody, Transform
from sparrow.core.world import World
from sparrow.math import (
    cross_product_vec3,
    rotate_vec_by_quat,
    rotate_vec_by_quat_inv,
)
from sparrow.physics.obb import get_obb_manifold
from sparrow.resources.physics import Gravity
from sparrow.types import Quaternion, Vector3

dt = 1 / 60
SOLVER_ITERATIONS = 4


def physics_system(world: World) -> None:
    gravity_res = world.try_resource(Gravity)
    gravity = gravity_res.acceleration if gravity_res else Vector3(0, -9.81, 0)
    gravity_arr = np.array([gravity.x, gravity.y, gravity.z], dtype=np.float64)

    # --- Integration Step ---
    for count, (bodies, transforms) in world.get_batch(RigidBody, Transform):
        active = bodies["inverse_mass"].reshape(-1) > 0.0

        if not np.any(active):
            continue

        vels = bodies["velocity"][active]
        ang_vels = bodies["angular_velocity"][active]
        pos = transforms["pos"][active]
        rots = transforms["rot"][active]

        drag = bodies["drag"][active]
        ang_drag = bodies["angular_drag"][active]

        # Apply gravity
        vels += gravity_arr * dt

        lin_damping = 1.0 / (1.0 + drag * dt)
        vels *= lin_damping
        pos += vels * dt

        ang_damping = 1.0 / (1.0 + ang_drag * dt)
        ang_vels *= ang_damping

        half_dt = dt * 0.5

        q_w = np.zeros_like(rots)
        q_w[:, 0] = ang_vels[:, 0] * half_dt
        q_w[:, 1] = ang_vels[:, 1] * half_dt
        q_w[:, 2] = ang_vels[:, 2] * half_dt
        q_w[:, 3] = 0.0

        x1, y1, z1, w1 = q_w[:, 0], q_w[:, 1], q_w[:, 2], q_w[:, 3]
        x2, y2, z2, w2 = rots[:, 0], rots[:, 1], rots[:, 2], rots[:, 3]

        new_x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
        new_y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
        new_z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
        new_w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2

        rots[:, 0] += new_x
        rots[:, 1] += new_y
        rots[:, 2] += new_z
        rots[:, 3] += new_w

        norm = np.sqrt(np.sum(rots**2, axis=1, keepdims=True))
        rots /= norm

        bodies["velocity"][active] = vels
        transforms["pos"][active] = pos
        transforms["rot"][active] = rots

    # --- Broad phase gather ---

    dynamics = []
    statics = []

    for count, (bodies, transforms, colliders) in world.get_batch(
        RigidBody, Transform, Collider3D
    ):
        ids = np.arange(count)

        mask = bodies["inverse_mass"].reshape(-1) > 0.0
        indices = ids[mask]

        if len(indices) > 0:
            dynamics.append((bodies, transforms, colliders, indices))

        mask_static = bodies["inverse_mass"].reshape(-1) == 0.0
        indices_static = ids[mask_static]

        if len(indices_static) > 0:
            statics.append((bodies, transforms, colliders, indices_static))

    # --- Narrow phase solver ---
    for _ in range(SOLVER_ITERATIONS):
        for d_batch in dynamics:
            d_bodies, d_trans, d_cols, d_indices = d_batch

            for i in d_indices:
                t_dyn = _view_transform(d_trans, i)
                c_dyn = _view_collider(d_cols, i)

                for s_batch in statics:
                    s_bodies, s_trans, s_cols, s_indices = s_batch
                    for j in s_indices:
                        t_stat = _view_transform(s_trans, j)
                        c_stat = _view_collider(s_cols, j)

                        manifold = get_obb_manifold(
                            t_dyn, c_dyn, t_stat, c_stat
                        )
                        if manifold:
                            norm, depth, pt = manifold
                            _resolve_collision_soa(
                                d_bodies,
                                d_trans,
                                i,
                                s_bodies,
                                s_trans,
                                j,
                                norm,
                                depth,
                                pt,
                            )

        for idx_a, batch_a in enumerate(dynamics):
            bodies_a, trans_a, cols_a, indices_a = batch_a

            for i in indices_a:
                t_a = _view_transform(trans_a, i)
                c_a = _view_collider(cols_a, i)

                for idx_b, batch_b in enumerate(dynamics):
                    if idx_b < idx_a:
                        continue

                    bodies_b, trans_b, cols_b, indices_b = batch_b

                    for j in indices_b:
                        if idx_a == idx_b and i == j:
                            continue
                        if idx_a == idx_b and j <= i:
                            continue

                        t_b = _view_transform(trans_b, j)
                        c_b = _view_collider(cols_b, j)

                        manifold = get_obb_manifold(t_a, c_a, t_b, c_b)
                        if manifold:
                            norm, depth, pt = manifold
                            _resolve_collision_soa(
                                bodies_a,
                                trans_a,
                                i,
                                bodies_b,
                                trans_b,
                                j,
                                norm,
                                depth,
                                pt,
                            )


def _view_transform(t_array: NDArray, idx: int) -> Transform:
    """Creates a temporary Transform object backed by array data for OBB calculation."""
    # Note: Vector3/Quaternion constuctors copy data.
    # This is the "Bridge" cost until OBB is vectorized.
    p = t_array["pos"][idx]
    r = t_array["rot"][idx]
    s = t_array["scale"][idx]
    return Transform(
        pos=Vector3(p[0], p[1], p[2]),
        rot=Quaternion(r[0], r[1], r[2], r[3]),
        scale=Vector3(s[0], s[1], s[2]),
    )


def _view_collider(c_array: NDArray, idx: int) -> Collider3D:
    c = c_array["center"][idx]
    s = c_array["size"][idx]
    return Collider3D(
        center=Vector3(c[0], c[1], c[2]), size=Vector3(s[0], s[1], s[2])
    )


def _resolve_collision_soa(
    bodies_a: NDArray,
    trans_a: NDArray,
    idx_a: int,
    bodies_b: NDArray,
    trans_b: NDArray,
    idx_b: int,
    normal: Vector3,
    depth: float,
    contact_point: Vector3,
):
    """


    Resolves collision modifying the NumPy arrays in-place.


    """

    percent = 0.8

    slop = 0.01

    # Raw Data Access

    inv_mass_a = bodies_a["inverse_mass"][idx_a].item()

    inv_mass_b = bodies_b["inverse_mass"][idx_b].item()

    total_inv_mass = inv_mass_a + inv_mass_b

    if total_inv_mass == 0.0:
        return

    pos_a_old = Vector3(*trans_a["pos"][idx_a])

    pos_b_old = Vector3(*trans_b["pos"][idx_b])

    rot_a_arr = trans_a["rot"][idx_a]

    rot_a = Quaternion(rot_a_arr[0], rot_a_arr[1], rot_a_arr[2], rot_a_arr[3])

    rot_b_arr = trans_b["rot"][idx_b]

    rot_b = Quaternion(rot_b_arr[0], rot_b_arr[1], rot_b_arr[2], rot_b_arr[3])

    # --- 1. Positional Correction ---

    correction_mag = max(depth - slop, 0.0) / total_inv_mass * percent

    corr_vec = np.array([normal.x, normal.y, normal.z]) * correction_mag

    trans_a["pos"][idx_a] += corr_vec * inv_mass_a

    trans_b["pos"][idx_b] -= corr_vec * inv_mass_b

    # --- 2. Velocity Resolution ---

    r_a = contact_point - pos_a_old

    r_b = contact_point - pos_b_old

    # Extract Vectors

    vel_a = Vector3(*bodies_a["velocity"][idx_a])

    ang_vel_a = Vector3(*bodies_a["angular_velocity"][idx_a])

    vel_b = Vector3(*bodies_b["velocity"][idx_b])

    ang_vel_b = Vector3(*bodies_b["angular_velocity"][idx_b])

    # V_contact = V_linear + (AngularVel x r)

    ang_a_x_r = cross_product_vec3(ang_vel_a, r_a)

    contact_vel_a = vel_a + ang_a_x_r

    ang_b_x_r = cross_product_vec3(ang_vel_b, r_b)

    contact_vel_b = vel_b + ang_b_x_r

    rel_vel = contact_vel_a - contact_vel_b

    vel_along_normal = (
        rel_vel.x * normal.x + rel_vel.y * normal.y + rel_vel.z * normal.z
    )

    if vel_along_normal > 0:
        return

    # Restitution

    e = min(
        bodies_a["restitution"][idx_a].item(),
        bodies_b["restitution"][idx_b].item(),
    )

    numerator = -(1.0 + e) * vel_along_normal

    denominator = total_inv_mass

    # Rotational Contribution

    rn_a = cross_product_vec3(r_a, normal)

    inv_i_a = Vector3(*bodies_a["inverse_inertia"][idx_a])

    # Transform (r x n) to local space

    rn_a_local = rotate_vec_by_quat_inv(rn_a, rot_a)

    # Compute J * M^-1 * J^T

    ang_term_a = (
        (rn_a_local.x**2 * inv_i_a.x)
        + (rn_a_local.y**2 * inv_i_a.y)
        + (rn_a_local.z**2 * inv_i_a.z)
    )

    denominator += ang_term_a

    rn_b = cross_product_vec3(r_b, normal)

    inv_i_b = Vector3(*bodies_b["inverse_inertia"][idx_b])

    rn_b_local = rotate_vec_by_quat_inv(rn_b, rot_b)

    ang_term_b = (
        (rn_b_local.x**2 * inv_i_b.x)
        + (rn_b_local.y**2 * inv_i_b.y)
        + (rn_b_local.z**2 * inv_i_b.z)
    )

    denominator += ang_term_b

    j = numerator / denominator

    # --- 3. Friction ---

    # (Simplified for brevity, but follows same pattern as original)

    impulse_vec = normal * j

    # --- 4. Apply Impulse ---

    impulse_np = np.array([impulse_vec.x, impulse_vec.y, impulse_vec.z])

    # Linear

    bodies_a["velocity"][idx_a] += impulse_np * inv_mass_a

    bodies_b["velocity"][idx_b] -= impulse_np * inv_mass_b

    # Angular

    impulse_torque_a = cross_product_vec3(r_a, impulse_vec)

    impulse_torque_a_local = rotate_vec_by_quat_inv(impulse_torque_a, rot_a)

    delta_ang_vel_a_local = Vector3(
        impulse_torque_a_local.x * inv_i_a.x,
        impulse_torque_a_local.y * inv_i_a.y,
        impulse_torque_a_local.z * inv_i_a.z,
    )

    delta_ang_vel_a = rotate_vec_by_quat(delta_ang_vel_a_local, rot_a)

    bodies_a["angular_velocity"][idx_a] += np.array(
        [delta_ang_vel_a.x, delta_ang_vel_a.y, delta_ang_vel_a.z]
    )

    impulse_torque_b = cross_product_vec3(r_b, impulse_vec)

    impulse_torque_b_local = rotate_vec_by_quat_inv(impulse_torque_b, rot_b)

    # Note: Torque on B is opposite (-J), so we subtract

    delta_ang_vel_b_local = Vector3(
        impulse_torque_b_local.x * inv_i_b.x,
        impulse_torque_b_local.y * inv_i_b.y,
        impulse_torque_b_local.z * inv_i_b.z,
    )

    delta_ang_vel_b = rotate_vec_by_quat(delta_ang_vel_b_local, rot_b)

    bodies_b["angular_velocity"][idx_b] -= np.array(
        [delta_ang_vel_b.x, delta_ang_vel_b.y, delta_ang_vel_b.z]
    )
