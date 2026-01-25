from typing import Optional, Tuple

from sparrow.core.components import Collider3D, Transform
from sparrow.types import Vector3


def get_world_aabb(
    trans: Transform, col: Collider3D
) -> Tuple[Vector3, Vector3]:
    """
    Calculate the world-space center and half-extents of the collider,
    accounting for the Transform's scale.
    """
    sx = col.half_size.x * abs(trans.scale.x)
    sy = col.half_size.y * abs(trans.scale.y)
    sz = col.half_size.z * abs(trans.scale.z)
    scaled_half_size = Vector3(sx, sy, sz)

    ox = col.center.x * trans.scale.x
    oy = col.center.y * trans.scale.y
    oz = col.center.z * trans.scale.z
    scaled_center_offset = Vector3(ox, oy, oz)

    global_center = trans.pos + scaled_center_offset

    return global_center, scaled_half_size


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
