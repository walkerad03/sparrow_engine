# sparrow/assets/types.py
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class VertexLayout:
    """Describes vertex attributes for VAO creation."""

    attributes: List[str]  # e.g. ["in_pos", "in_normal", "in_uv"]
    format: str  # moderngl buffer format string e.g. "3f 3f 2f"
    stride_bytes: int  # e.g. 32


@dataclass(frozen=True)
class MeshData:
    """Raw mesh data loaded from disk, ready for GPU upload."""

    vertices: bytes
    vertex_layout: VertexLayout
    aabb: Tuple[Tuple[float, float, float], Tuple[float, float, float]]
    indices: Optional[bytes] = None
    index_count: int = 0


@dataclass(frozen=True)
class TextureData:
    """Raw texture data and metadata."""

    data: bytes
    width: int
    height: int
    components: int  # 3 (RGB) or 4 (RGBA)


@dataclass(frozen=True)
class ShaderSource:
    """Raw shader source code."""

    source: str
    path: str  # For debugging / error reporting.
