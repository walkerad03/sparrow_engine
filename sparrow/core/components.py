# sparrow/core/components.py
from dataclasses import dataclass

from sparrow.types import Quaternion, Vector3


@dataclass
class Transform:
    pos: Vector3 = Vector3(0.0, 0.0, 0.0)
    rot: Quaternion = Quaternion.identity()
    scale: Vector3 = Vector3(1.0, 1.0, 1.0)

    _grid_key: int = 0


@dataclass
class Velocity:
    ds: Vector3 = Vector3(0.0, 0.0, 0.0)
