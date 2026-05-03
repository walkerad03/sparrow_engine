from dataclasses import dataclass

from sparrow.types import Vector3


@dataclass
class RigidBody:
    body_id: int = -1
    mass: float = 1.0


@dataclass
class Collider:
    shape_type: int = 0
    extents: Vector3 = Vector3(1.0, 1.0, 1.0)
