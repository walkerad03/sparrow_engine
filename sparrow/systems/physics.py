from dataclasses import replace
from typing import Optional, Tuple

from sparrow.core.components import Collider3D, RigidBody, Transform
from sparrow.core.world import World
from sparrow.helpers.physics import get_world_aabb
from sparrow.resources.physics import Gravity
from sparrow.types import EntityId, Vector3

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

        updated_trans = replace(transform, pos=new_pos)
        updated_body = replace(body, velocity=new_vel)

        world.mutate_component(eid, updated_trans)
        world.mutate_component(eid, updated_body)

        if world.has(eid, Collider3D):
            collider = world.component(eid, Collider3D)
            dynamic_entities.append(
                (eid, updated_body, updated_trans, collider)
            )

    statics = []
    for eid, col, trans in world.join(Collider3D, Transform):
        if not world.has(eid, RigidBody):
            statics.append((eid, None, trans, col))

    for _ in range(SOLVER_ITERATIONS):
        for i in range(len(dynamic_entities)):
            dyn_eid, _, _, dyn_col = dynamic_entities[i]

            dyn_trans = world.component(dyn_eid, Transform)
            dyn_body = world.component(dyn_eid, RigidBody)

            if not dyn_body or not dyn_trans:
                continue

            for stat in statics:
                stat_eid, _, stat_trans, stat_col = stat

                manifold = _get_aabb_manifold(
                    dyn_trans, dyn_col, stat_trans, stat_col
                )

                if manifold:
                    normal, depth = manifold
                    _resolve_collision(
                        world,
                        dyn_eid,
                        dyn_body,
                        dyn_trans,
                        None,
                        None,
                        normal,
                        depth,
                    )

        for i in range(len(dynamic_entities)):
            id_a, _, _, col_a = dynamic_entities[i]
            trans_a = world.component(id_a, Transform)
            body_a = world.component(id_a, RigidBody)
            if not trans_a or not body_a:
                continue

            for j in range(i + 1, len(dynamic_entities)):
                id_b, _, _, col_b = dynamic_entities[j]
                trans_b = world.component(id_b, Transform)
                body_b = world.component(id_b, RigidBody)
                if not trans_b or not body_b:
                    continue

                manifold = _get_aabb_manifold(trans_a, col_a, trans_b, col_b)
                if manifold:
                    normal, depth = manifold
                    _resolve_collision(
                        world,
                        id_a,
                        body_a,
                        trans_a,
                        body_b,
                        trans_b,
                        normal,
                        depth,
                        id_b=id_b,
                    )


def _get_aabb_manifold(
    t1: Transform, c1: Collider3D, t2: Transform, c2: Collider3D
) -> Optional[Tuple[Vector3, float]]:
    center1, half1 = get_world_aabb(t1, c1)
    center2, half2 = get_world_aabb(t2, c2)

    diff = center1 - center2

    extent_sum_x = half1.x + half2.x
    extent_sum_y = half1.y + half2.y
    extent_sum_z = half1.z + half2.z

    overlap_x = extent_sum_x - abs(diff.x)
    if overlap_x <= 0:
        return None  # Separated on X

    overlap_y = extent_sum_y - abs(diff.y)
    if overlap_y <= 0:
        return None  # Separated on Y

    overlap_z = extent_sum_z - abs(diff.z)
    if overlap_z <= 0:
        return None  # Separated on Z

    depth = overlap_x
    normal = Vector3(1.0 if diff.x > 0 else -1.0, 0.0, 0.0)

    if overlap_y < depth:
        depth = overlap_y
        normal = Vector3(0.0, 1.0 if diff.y > 0 else -1.0, 0.0)

    if overlap_z < depth:
        depth = overlap_z
        normal = Vector3(0.0, 0.0, 1.0 if diff.z > 0 else -1.0)

    return (normal, depth)


def _resolve_collision(
    world: World,
    id_a: EntityId,
    body_a: RigidBody,
    trans_a: Transform,
    body_b: RigidBody | None,
    trans_b: Transform | None,
    normal: Vector3,
    depth: float,
    id_b: EntityId = EntityId(-1),
):
    percent = 0.8
    slop = 0.01

    inv_mass_a = body_a.inverse_mass
    inv_mass_b = body_b.inverse_mass if body_b else 0.0
    total_inv_mass = inv_mass_a + inv_mass_b

    if total_inv_mass == 0.0:
        return

    correction_magnitude = max(depth - slop, 0.0) / total_inv_mass * percent
    correction = normal * correction_magnitude

    pos_a = trans_a.pos + (correction * inv_mass_a)
    world.mutate_component(id_a, replace(trans_a, pos=pos_a))

    if body_b and trans_b:
        pos_b = trans_b.pos - (correction * inv_mass_b)
        world.mutate_component(id_b, replace(trans_b, pos=pos_b))

    vel_a = body_a.velocity
    vel_b = body_b.velocity if body_b else Vector3.zero()
    relative_vel = vel_a - vel_b

    vel_along_normal = (
        relative_vel.x * normal.x
        + relative_vel.y * normal.y
        + relative_vel.z * normal.z
    )

    if vel_along_normal > 0:
        return

    e = body_a.restitution
    if body_b:
        e = min(body_a.restitution, body_b.restitution)

    j = -(1.0 + e) * vel_along_normal
    j /= total_inv_mass

    # Apply Impulse
    impulse = normal * j

    new_vel_a = body_a.velocity + (impulse * inv_mass_a)
    world.mutate_component(id_a, replace(body_a, velocity=new_vel_a))

    if body_b:
        new_vel_b = body_b.velocity - (impulse * inv_mass_b)
        world.mutate_component(id_b, replace(body_b, velocity=new_vel_b))
