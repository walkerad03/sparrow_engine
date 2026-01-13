# sparrow/graphics/renderer/settings.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PresentScaleMode(str, Enum):
    """How logical output is mapped to the window."""

    STRETCH = "stretch"
    FIT = "fit"
    INTEGER_FIT = "integer_fit"


@dataclass(frozen=True, slots=True)
class ResolutionSettings:
    """Resolution policy for internal rendering and presentation."""

    logical_width: int
    logical_height: int
    scale_mode: PresentScaleMode = PresentScaleMode.STRETCH


@dataclass(frozen=True, slots=True)
class DeferredRendererSettings:
    """Deferred renderer configuration. Extend as needed."""

    resolution: ResolutionSettings
    hdr: bool = True
    msaa_samples: int = 1
    enable_debug_views: bool = False
