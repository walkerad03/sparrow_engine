# sparrow/physics/obb.py
from typing import Optional, Tuple

import numpy as np

from sparrow.core.components import Collider3D, Transform
from sparrow.types import Vector3


def get_support_point(
    t: Transform, c: Collider3D, direction: np.ndarray
) -> Vector3:
    """
    Find the vertex of the OBB furthest in the given direction.
    """
    rot = t.rot.to_matrix4()[:3, :3]

    vertices = []

    sx, sy, sz = (
        c.size.x * t.scale.x * 0.5,
        c.size.y * t.scale.y * 0.5,
        c.size.z * t.scale.z * 0.5,
    )
    cx, cy, cz = (
        c.center.x * t.scale.x,
        c.center.y * t.scale.y,
        c.center.z * t.scale.z,
    )

    signs = [-1, 1]
    for x in signs:
        for y in signs:
            for z in signs:
                # Local Vertex
                local_v = np.array([cx + x * sx, cy + y * sy, cz + z * sz])
                # World Vertex
                world_v = t.pos + Vector3(*(rot @ local_v))
                vertices.append(world_v)

    best_proj = -float("inf")
    best_point = Vector3(0, 0, 0)

    for v in vertices:
        # Dot product: v . direction
        proj = v.x * direction[0] + v.y * direction[1] + v.z * direction[2]
        if proj > best_proj:
            best_proj = proj
            best_point = v

    return best_point


def get_obb_manifold(
    t1: Transform, c1: Collider3D, t2: Transform, c2: Collider3D
) -> Optional[Tuple[Vector3, float, Vector3]]:
    pass
    """
    Checks collision between two Oriented Bounding Boxes (OBB) using SAT.
    Returns the Minimum Translation Vector (Normal * Depth).
    """
    # Rotation Matrices (3x3)
    rot1 = t1.rot.to_matrix4()[:3, :3]
    rot2 = t2.rot.to_matrix4()[:3, :3]

    # Center positions
    offset1_local = np.array(
        [
            c1.center.x * t1.scale.x,
            c1.center.y * t1.scale.y,
            c1.center.z * t1.scale.z,
        ]
    )
    offset1_world = rot1 @ offset1_local
    pos1 = np.array([t1.pos.x, t1.pos.y, t1.pos.z]) + offset1_world

    offset2_local = np.array(
        [
            c2.center.x * t2.scale.x,
            c2.center.y * t2.scale.y,
            c2.center.z * t2.scale.z,
        ]
    )
    offset2_world = rot2 @ offset2_local
    pos2 = np.array([t2.pos.x, t2.pos.y, t2.pos.z]) + offset2_world

    # Half-extents (scaled)
    ext1 = (
        np.array(
            [
                c1.size.x * abs(t1.scale.x),
                c1.size.y * abs(t1.scale.y),
                c1.size.z * abs(t1.scale.z),
            ]
        )
        * 0.5
    )

    ext2 = (
        np.array(
            [
                c2.size.x * abs(t2.scale.x),
                c2.size.y * abs(t2.scale.y),
                c2.size.z * abs(t2.scale.z),
            ]
        )
        * 0.5
    )

    axes = []
    for i in range(3):
        axes.append(rot1[:, i])
    for i in range(3):
        axes.append(rot2[:, i])

    for i in range(3):
        for j in range(3):
            axis = np.cross(rot1[:, i], rot2[:, j])
            if np.linalg.norm(axis) > 0.001:
                axes.append(axis / np.linalg.norm(axis))

    min_overlap = float("inf")
    collision_normal = None

    t_vec = pos2 - pos1

    for axis in axes:
        proj1 = (
            abs(np.dot(axis, rot1[:, 0])) * ext1[0]
            + abs(np.dot(axis, rot1[:, 1])) * ext1[1]
            + abs(np.dot(axis, rot1[:, 2])) * ext1[2]
        )

        proj2 = (
            abs(np.dot(axis, rot2[:, 0])) * ext2[0]
            + abs(np.dot(axis, rot2[:, 1])) * ext2[1]
            + abs(np.dot(axis, rot2[:, 2])) * ext2[2]
        )

        dist = abs(np.dot(t_vec, axis))

        overlap = (proj1 + proj2) - dist

        if overlap <= 0:
            return None

        if overlap < min_overlap:
            min_overlap = overlap
            collision_normal = axis

            if np.dot(collision_normal, t_vec) > 0:
                collision_normal = -collision_normal

    if collision_normal is None:
        return None

    pA = get_support_point(t1, c1, -collision_normal)
    pB = get_support_point(t2, c2, collision_normal)
    contact_point = (pA + pB) * 0.5

    normal_v = Vector3(
        collision_normal[0], collision_normal[1], collision_normal[2]
    )
    return normal_v, min_overlap, contact_point
