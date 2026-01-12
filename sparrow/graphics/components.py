from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sparrow.core.component import Component

RenderDomain = Literal["sprite", "mesh"]
BlendMode = Literal["opaque", "alpha", "add"]


@dataclass(frozen=True)
class Renderable(Component):
    mesh_id: str
    material: str

    domain: RenderDomain = "sprite"
    blend: BlendMode = "alpha"

    casts_shadows: bool = True
    receives_shadows: bool = True

    # Optional ordering hint (mainly for 2.5D)
    sort_key: int = 0
