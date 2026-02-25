# sparrow/core/components.py
from dataclasses import dataclass

from sparrow.types import Quaternion, Vector3


@dataclass
class Transform:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    pos: Vector3 = Vector3(0.0, 0.0, 0.0)
    rot: Quaternion = Quaternion.identity()
    scale: Vector3 = Vector3(1.0, 1.0, 1.0)


@dataclass
class Velocity:
    dx: float = 0.0
    dy: float = 0.0
    dz: float = 0.0

    ds: Vector3 = Vector3(0.0, 0.0, 0.0)
