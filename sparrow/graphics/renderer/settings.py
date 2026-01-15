# sparrow/graphics/renderer/settings.py
from __future__ import annotations

import datetime
from abc import ABC
from dataclasses import dataclass
from enum import Enum

from sparrow.graphics.helpers.nishita import get_sun_dir_from_datetime


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


_default_time = datetime.datetime(2023, 10, 27, 15, 0, 0)


@dataclass(slots=True)
class SunlightSettings:
    """Policy for global directional light."""

    direction: tuple[float, float, float] = get_sun_dir_from_datetime(
        _default_time, 40.71, -74.00
    )
    color: tuple[float, float, float] = (1.0, 0.9294, 0.8706)


@dataclass(frozen=True, slots=True)
class RendererSettings(ABC):
    """Base class for all rendering pipeline configurations."""

    resolution: ResolutionSettings
    sunlight: SunlightSettings


@dataclass(frozen=True, slots=True)
class DeferredRendererSettings(RendererSettings):
    """Deferred renderer configuration."""

    hdr: bool = True
    msaa_samples: int = 1


@dataclass(frozen=True, slots=True)
class ForwardRendererSettings(RendererSettings):
    """Forward renderer configuration."""

    msaa_samples: int = 4
    hdr: bool = False


@dataclass(frozen=True, slots=True)
class RaytracingRendererSettings(RendererSettings):
    """Forward renderer configuration."""

    max_bounces: int = 2
    samples_per_pixel: int = 1
    denoiser_enabled: bool = True


@dataclass(frozen=True, slots=True)
class BlitRendererSettings(RendererSettings):
    """Forward renderer configuration."""

    ...
