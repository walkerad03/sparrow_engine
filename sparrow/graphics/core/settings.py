# sparrow/graphics/core/settings.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class PresentScaleMode(str, Enum):
    STRETCH = "stretch"
    FIT = "fit"
    INTEGER_FIT = "integer_fit"


@dataclass(slots=True)
class ResolutionSettings:
    """
    Resource: Controls the logical and physical resolution.
    """

    logical_width: int = 1920
    logical_height: int = 1080
    scale_mode: PresentScaleMode = PresentScaleMode.FIT
    vsync: bool = True


@dataclass(slots=True)
class SunlightSettings:
    """
    Resource: Controls the primary directional light (The Sun).
    """

    direction: Tuple[float, float, float] = (0.5, -0.8, 0.2)
    color: Tuple[float, float, float] = (1.0, 0.98, 0.9)
    intensity: float = 1.0


@dataclass(slots=True)
class RendererSettings:
    """
    Resource: The master configuration object found in the World.
    """

    resolution: ResolutionSettings = field(default_factory=ResolutionSettings)
    sunlight: SunlightSettings = field(default_factory=SunlightSettings)

    shadows_enabled: bool = False
    bloom_enabled: bool = False
    debug_wireframe: bool = False
