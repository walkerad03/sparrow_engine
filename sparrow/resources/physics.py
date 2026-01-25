from dataclasses import dataclass

from sparrow.types import Vector3


@dataclass(frozen=True)
class Gravity:
    acceleration = Vector3(0.0, -9.81, 0.0)
