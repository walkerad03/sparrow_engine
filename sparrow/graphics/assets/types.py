# sparrow/graphics/assets/types.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple


@dataclass(frozen=True, slots=True)
class VertexLayout:
    """Describes vertex attributes for VAO creation."""

    attributes: Sequence[str]  # e.g. ["in_pos", "in_normal", "in_uv"]
    format: str  # moderngl buffer format string
    stride_bytes: int


@dataclass(frozen=True, slots=True)
class MeshData:
    """CPU-side mesh payload used to create GPU buffers."""

    vertices: bytes
    indices: Optional[bytes]
    vertex_layout: VertexLayout
    aabb: Tuple[Tuple[float, float, float], Tuple[float, float, float]]
    index_element_size: int = 4  # bytes (2 or 4)
