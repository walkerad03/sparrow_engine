# sparrow/core/components.py
from dataclasses import dataclass


@dataclass
class Transform:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class Velocity:
    dx: float = 0.0
    dy: float = 0.0
    dz: float = 0.0
