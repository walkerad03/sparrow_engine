import math
from dataclasses import replace

from sparrow.core.components import Collider3D, RigidBody, Transform
from sparrow.core.world import World
from sparrow.math import cross_product_vec3, mul_quat
from sparrow.physics.obb import get_obb_manifold
from sparrow.resources.physics import Gravity
from sparrow.types import EntityId, Quaternion, Vector3

dt = 1 / 60
SOLVER_ITERATIONS = 4


def physics_system(world: World) -> None:
    gravity = world.try_resource(Gravity)
    if not gravity:
        return

    dynamic_entities = []
    for eid, body, transform in world.join(RigidBody, Transform):
        if body.inverse_mass == 0.0:
            continue

        new_vel_y = body.velocity.y + (gravity.acceleration.y * dt)
        new_vel = replace(body.velocity, y=new_vel_y)

        damping = 1.0 / (1.0 + body.drag * dt)
        new_vel = new_vel * damping
        new_pos = transform.pos + (new_vel * dt)

        ang_damping = 1.0 / (1.0 + body.angular_drag * dt)
        new_ang_vel = body.angular_velocity * ang_damping
        new_rot = _integrate_rotation(transform.rot, new_ang_vel, dt)

        updated_trans = replace(transform, pos=new_pos, rot=new_rot)
        updated_body = replace(
            body, velocity=new_vel, angular_velocity=new_ang_vel
        )

        world.mutate_component(eid, updated_trans)
        world.mutate_component(eid, updated_body)

        if world.has(eid, Collider3D):
            collider = world.component(eid, Collider3D)
            dynamic_entities.append((eid, collider))

    statics = []
    for eid, col, trans in world.join(Collider3D, Transform):
        if not world.has(eid, RigidBody):
            statics.append((eid, None, trans, col))

    for _ in range(SOLVER_ITERATIONS):
        for i in range(len(dynamic_entities)):
            dyn_eid, dyn_col = dynamic_entities[i]

            dyn_trans = world.component(dyn_eid, Transform)
            dyn_body = world.component(dyn_eid, RigidBody)

            if not dyn_body or not dyn_trans:
                continue

            for stat in statics:
                stat_eid, _, stat_trans, stat_col = stat

                manifold = get_obb_manifold(
                    dyn_trans, dyn_col, stat_trans, stat_col
                )

                if manifold:
                    normal, depth, contact_point = manifold
                    _resolve_collision(
                        world,
                        dyn_eid,
                        dyn_body,
                        dyn_trans,
                        None,
                        None,
                        normal,
                        depth,
                        contact_point,
                    )
                    dyn_trans = world.component(dyn_eid, Transform)
                    dyn_body = world.component(dyn_eid, RigidBody)

        for i in range(len(dynamic_entities)):
            id_a, col_a = dynamic_entities[i]
            trans_a = world.component(id_a, Transform)
            body_a = world.component(id_a, RigidBody)
            if not trans_a or not body_a:
                continue

            for j in range(i + 1, len(dynamic_entities)):
                id_b, col_b = dynamic_entities[j]
                trans_b = world.component(id_b, Transform)
                body_b = world.component(id_b, RigidBody)
                if not trans_b or not body_b:
                    continue

                manifold = get_obb_manifold(trans_a, col_a, trans_b, col_b)
                if manifold:
                    normal, depth, contact_point = manifold
                    _resolve_collision(
                        world,
                        id_a,
                        body_a,
                        trans_a,
                        body_b,
                        trans_b,
                        normal,
                        depth,
                        contact_point,
                        id_b=id_b,
                    )
                    trans_a = world.component(id_a, Transform)
                    body_a = world.component(id_a, RigidBody)


def _resolve_collision(
    world: World,
    id_a: EntityId,
    body_a: RigidBody,
    trans_a: Transform,
    body_b: RigidBody | None,
    trans_b: Transform | None,
    normal: Vector3,
    depth: float,
    contact_point: Vector3,
    id_b: EntityId = EntityId(-1),
):
    percent = 0.8
    slop = 0.01

    inv_mass_a = body_a.inverse_mass
    inv_mass_b = body_b.inverse_mass if body_b else 0.0
    total_inv_mass = inv_mass_a + inv_mass_b

    if total_inv_mass == 0.0:
        return

    # positional correction
    correction_magnitude = max(depth - slop, 0.0) / total_inv_mass * percent
    correction = normal * correction_magnitude

    pos_a = trans_a.pos + (correction * inv_mass_a)
    world.mutate_component(id_a, replace(trans_a, pos=pos_a))

    if body_b and trans_b:
        pos_b = trans_b.pos - (correction * inv_mass_b)
        world.mutate_component(id_b, replace(trans_b, pos=pos_b))

    # compute lever arms
    r_a = contact_point - trans_a.pos
    r_b = Vector3(0.0, 0.0, 0.0)
    if trans_b:
        r_b = contact_point - trans_b.pos

    # Velocity at contact point
    # V_contact = V_linear + (AngularVel x r)
    ang_vel_a_cross_r = cross_product_vec3(body_a.angular_velocity, r_a)
    contact_vel_a = body_a.velocity + ang_vel_a_cross_r

    contact_vel_b = Vector3(0.0, 0.0, 0.0)
    if body_b:
        ang_vel_b_cross_r = cross_product_vec3(body_b.angular_velocity, r_b)
        contact_vel_b = body_b.velocity + ang_vel_b_cross_r

    relative_vel = contact_vel_a - contact_vel_b

    # compute impulse magnitude (J)
    vel_along_normal = (
        relative_vel.x * normal.x
        + relative_vel.y * normal.y
        + relative_vel.z * normal.z
    )

    # do not resolve if velocities are separating
    if vel_along_normal > 0:
        return

    e = body_a.restitution
    if body_b:
        e = min(body_a.restitution, body_b.restitution)

    numerator = -(1.0 + e) * vel_along_normal
    denominator = total_inv_mass

    # Body A Rotation contribution
    rn_a = cross_product_vec3(r_a, normal)
    i_inv_a = body_a.inverse_inertia
    ang_term_a = (
        (rn_a.x**2 * i_inv_a.x)
        + (rn_a.y**2 * i_inv_a.y)
        + (rn_a.z**2 * i_inv_a.z)
    )
    denominator += ang_term_a

    # Body B Rotational Contribution
    i_inv_b = Vector3(0, 0, 0)
    if body_b:
        rn_b = cross_product_vec3(r_b, normal)
        i_inv_b = body_b.inverse_inertia
        ang_term_b = (
            (rn_b.x**2 * i_inv_b.x)
            + (rn_b.y**2 * i_inv_b.y)
            + (rn_b.z**2 * i_inv_b.z)
        )
        denominator += ang_term_b

    j = numerator / denominator

    # Friction
    tangent = relative_vel - (normal * vel_along_normal)
    tangent_len = math.sqrt(tangent.x**2 + tangent.y**2 + tangent.z**2)
    friction_impulse = Vector3(0, 0, 0)

    if tangent_len > 0.0001:
        t = Vector3(
            tangent.x / tangent_len,
            tangent.y / tangent_len,
            tangent.z / tangent_len,
        )

        rn_a_t = cross_product_vec3(r_a, t)
        denom_t = (
            total_inv_mass
            + (rn_a_t.x**2 * i_inv_a.x)
            + (rn_a_t.y**2 * i_inv_a.y)
            + (rn_a_t.z**2 * i_inv_a.z)
        )

        if body_b:
            rn_b_t = cross_product_vec3(r_b, t)
            denom_t += (
                (rn_b_t.x**2 * i_inv_b.x)
                + (rn_b_t.y**2 * i_inv_b.y)
                + (rn_b_t.z**2 * i_inv_b.z)
            )

        jt = (
            -(
                relative_vel.x * t.x
                + relative_vel.y * t.y
                + relative_vel.z * t.z
            )
            / denom_t
        )

        mu = (
            (body_a.friction + body_b.friction) * 0.5
            if body_b
            else body_a.friction
        )
        max_jt = abs(mu * j)
        jt = max(-max_jt, min(max_jt, jt))

        friction_impulse = t * jt

    # Apply Impulse
    impulse_vec = (normal * j) + friction_impulse

    # Linear impulse A
    new_vel_a = body_a.velocity + (impulse_vec * inv_mass_a)

    # Angular impulse A (Torque)
    # dW = I_inv * (r x J)
    impulse_torque_a = cross_product_vec3(r_a, impulse_vec)
    new_ang_vel_a = body_a.angular_velocity + Vector3(
        impulse_torque_a.x * i_inv_a.x,
        impulse_torque_a.y * i_inv_a.y,
        impulse_torque_a.z * i_inv_a.z,
    )

    world.mutate_component(
        id_a,
        replace(body_a, velocity=new_vel_a, angular_velocity=new_ang_vel_a),
    )

    if body_b:
        # Subtract impluse for B
        new_vel_b = body_b.velocity - (impulse_vec * inv_mass_b)

        # Apply Angular Impulse B
        # Torque = r_b x (-J) = - (r_b x J)
        impulse_torque_b = cross_product_vec3(r_b, impulse_vec)
        new_ang_vel_b = body_b.angular_velocity - Vector3(
            impulse_torque_b.x * i_inv_b.x,
            impulse_torque_b.y * i_inv_b.y,
            impulse_torque_b.z * i_inv_b.z,
        )

        world.mutate_component(
            id_b,
            replace(body_b, velocity=new_vel_b, angular_velocity=new_ang_vel_b),
        )


def _integrate_rotation(
    rot: Quaternion, ang_vel: Vector3, dt: float
) -> Quaternion:
    """
    Integrates angular velocity into the rotation quaternion.
    dq/dt = 0.5 * w * q
    """
    q_w = Quaternion(
        ang_vel.x * dt * 0.5, ang_vel.y * dt * 0.5, ang_vel.z * dt * 0.5, 0.0
    )

    q_diff = mul_quat(q_w, rot)

    new_x = rot.x + q_diff.x
    new_y = rot.y + q_diff.y
    new_z = rot.z + q_diff.z
    new_w = rot.w + q_diff.w

    length = math.sqrt(new_x**2 + new_y**2 + new_z**2 + new_w**2)
    if length == 0:
        return rot
    inv = 1.0 / length
    return Quaternion(new_x * inv, new_y * inv, new_z * inv, new_w * inv)
