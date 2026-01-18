# sparrow/graphics/helpers/cubemaps.py
from __future__ import annotations

from dataclasses import dataclass

import moderngl


@dataclass(frozen=True, slots=True)
class CubemapDesc:
    """Descriptor for cubemap allocation."""

    size: int
    components: int
    dtype: str
    mipmaps: bool = True


def allocate_cubemap(
    ctx: moderngl.Context, desc: CubemapDesc, *, label: str = ""
) -> moderngl.TextureCube:
    """Allocate a cubemap texture with reasonable defaults."""
    raise NotImplementedError
