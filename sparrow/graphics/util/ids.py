# sparrow/graphics/util/ids.py
from __future__ import annotations

from dataclasses import dataclass
from typing import NewType

PassId = NewType("PassId", str)
ResourceId = NewType("ResourceId", str)
ShaderId = NewType("ShaderId", str)
MeshId = NewType("MeshId", str)
MaterialId = NewType("MaterialId", str)
TextureId = NewType("TextureId", str)


@dataclass(frozen=True, slots=True)
class Named:
    """Small helper for validated, human-readable names used across the renderer."""

    name: str
