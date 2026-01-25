# sparrow/graphics/ecs/frame_submit.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

import numpy as np


@dataclass(frozen=True, slots=True)
class CameraData:
    """Camera matrices and parameters required for rendering."""

    view: np.ndarray  # shape (4,4), float64
    proj: np.ndarray  # shape (4,4), float64
    view_proj: np.ndarray  # shape (4,4), float64
    position_ws: np.ndarray  # shape (3,), float64
    near: float
    far: float


@dataclass(frozen=True, slots=True)
class LightPoint:
    """Simple point light for deferred lighting."""

    position_ws: np.ndarray  # model transform matrix (3,)
    radius: float
    color_rgb: np.ndarray  # (3,)
    intensity: float
    light_id: int


@dataclass(frozen=True, slots=True)
class DrawItem:
    """
    A draw packet produced by ECS culling/visibility systems.

    The renderer should treat this as already filtered and sorted
    (or it can sort further based on its own policy).
    """

    mesh_id: str
    material_id: str
    model: np.ndarray  # model transform matrix (4,4)
    entity_id: int
    sort_key: int = 0  # optional packed sort key


@dataclass(frozen=True, slots=True)
class RenderFrameInput:
    """All inputs needed to render a frame."""

    frame_index: int
    dt_seconds: float
    camera: CameraData
    draws: Sequence[DrawItem]
    point_lights: Sequence[LightPoint]
    debug_flags: Optional[Mapping[str, bool]] = None
    viewport_width: Optional[int] = None
    viewport_height: Optional[int] = None
