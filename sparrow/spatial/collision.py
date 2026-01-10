from typing import Tuple

from ..core.components import BoxCollider, Transform
from ..types import Rect


def get_world_bounds(trans: Transform, collider: BoxCollider) -> Rect:
    """Calculates the world-space rectangle of a collider."""
    # Center position - Half Width + Offset
    left = trans.x + collider.offset[0] - (collider.width / 2)
    top = trans.y + collider.offset[1] - (collider.height / 2)
    return (left, top, collider.width, collider.height)


def aabb_vs_aabb(r1: Rect, r2: Rect) -> bool:
    """
    Rect = (x, y, w, h) where x,y is Top-Left corner.
    """
    return (
        r1[0] < r2[0] + r2[2]
        and r1[0] + r1[2] > r2[0]
        and r1[1] < r2[1] + r2[3]
        and r1[1] + r1[3] > r2[1]
    )


def point_vs_aabb(px: float, py: float, r: Rect) -> bool:
    return r[0] <= px <= r[0] + r[2] and r[1] <= py <= r[1] + r[3]


def circle_vs_circle(
    p1: Tuple[float, float], r1: float, p2: Tuple[float, float], r2: float
) -> bool:
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    dist_sq = dx * dx + dy * dy
    radius_sum = r1 + r2
    return dist_sq < (radius_sum * radius_sum)
