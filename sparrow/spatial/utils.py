import math
from typing import Tuple


def distance_sq(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Returns squared distance (faster than sqrt for comparisons)."""
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return dx * dx + dy * dy


def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.sqrt(distance_sq(p1, p2))


def normalize(v: Tuple[float, float]) -> Tuple[float, float]:
    """Returns a unit vector."""
    m = math.sqrt(v[0] * v[0] + v[1] * v[1])
    if m == 0:
        return (0.0, 0.0)
    return (v[0] / m, v[1] / m)
