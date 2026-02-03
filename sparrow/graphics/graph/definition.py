# sparrow/graphics/graph/definition.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from sparrow.graphics.utils.ids import ResourceId


@dataclass(frozen=True)
class TextureDesc:
    """
    Description of a texture resource managed by the graph.
    """

    size: Optional[Tuple[int, int]] = None  # None = Match Pipeline Resolution
    components: int = 4
    dtype: str = "f1"  # f1, f2, f4
    samples: int = 0  # MSAA samples (0 = none)

    # If explicit size is None, use this scale factor relative to screen
    size_scale: float = 1.0


@dataclass(frozen=True)
class BufferDesc:
    """
    Description of a buffer resource managed by the graph.
    """

    size_bytes: int
    dynamic: bool = True


@dataclass(frozen=True)
class FramebufferDesc:
    """
    A collection of textures used as a render target.
    """

    color_attachments: list[ResourceId]
    depth_attachment: Optional[ResourceId] = None
