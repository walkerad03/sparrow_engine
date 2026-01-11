from __future__ import annotations

from dataclasses import dataclass
from typing import List

from sparrow.graphics.components import Renderable
from sparrow.types import Quaternion, Vector3


@dataclass
class DrawItem:
    eid: int
    renderable: Renderable
    position: Vector3
    rotation: Quaternion
    scale: Vector3


@dataclass(slots=True)
class DrawLight:
    position: Vector3
    color: tuple[float, float, float, float]
    radius: float


@dataclass
class RenderDrawList:
    opaque: List[DrawItem]
    transparent: List[DrawItem]
    lights: List[DrawLight]

    @classmethod
    def empty(cls) -> RenderDrawList:
        return cls([], [], [])
