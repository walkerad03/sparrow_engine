# sparrow/graphics/assets/texture_manager.py
from __future__ import annotations

from dataclasses import dataclass

import moderngl

from sparrow.graphics.util.ids import TextureId


@dataclass(slots=True)
class TextureHandle:
    """Wraps a ModernGL texture and sampler parameters."""

    texture: moderngl.Texture | moderngl.TextureCube
    label: str


class TextureManager:
    """Creates and caches textures and cubemaps."""

    def __init__(self, gl: moderngl.Context) -> None: ...

    def create_2d(
        self,
        tex_id: TextureId,
        *,
        width: int,
        height: int,
        components: int,
        dtype: str,
        label: str = "",
    ) -> TextureHandle:
        """Allocate a 2D texture."""
        raise NotImplementedError

    def create_cubemap(
        self,
        tex_id: TextureId,
        *,
        size: int,
        components: int,
        dtype: str,
        label: str = "",
    ) -> TextureHandle:
        """Allocate a cubemap texture."""
        raise NotImplementedError

    def get(self, tex_id: TextureId) -> TextureHandle:
        """Retrieve an existing texture."""
        raise NotImplementedError
