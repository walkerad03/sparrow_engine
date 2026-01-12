from dataclasses import dataclass
from typing import Tuple

from sparrow.core.component import Component


@dataclass(frozen=True)
class PointLight(Component):
    """
    Omni-directional light source.
    """

    color: Tuple[float, float, float] = (1.0, 0.9, 0.7)  # Warm white
    radius: float = 128.0
    cast_shadows: bool = True


@dataclass(frozen=True)
class ConeLight(Component):
    """
    Directional light source (Flashlight/Lantern).
    """

    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    radius: float = 200.0
    angle: float = 45.0  # Cone width in degrees
    direction: float = 0.0  # Angle in radians
    cast_shadows: bool = True


@dataclass(frozen=True)
class AmbientLight(Component):
    """
    Global base light level.
    Usually very low (0.1) for 'The Old Wound' to ensure darkness.
    """

    color: Tuple[float, float, float] = (0.1, 0.1, 0.2)  # Dark blue tint


@dataclass(frozen=True)
class BlocksLight(Component):
    pass
