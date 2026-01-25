from typing import Tuple

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
