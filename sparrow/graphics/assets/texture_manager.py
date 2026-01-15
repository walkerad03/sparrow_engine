# sparrow/graphics/assets/texture_manager.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import moderngl

from sparrow.graphics.helpers.nishita import generate_nishita_sky_lut
from sparrow.graphics.util.ids import TextureId


@dataclass(slots=True)
class TextureHandle:
    """Wraps a ModernGL texture and sampler parameters."""

    texture: moderngl.Texture | moderngl.TextureCube
    label: str


class TextureManager:
    """Creates and caches textures and cubemaps."""

    def __init__(self, gl: moderngl.Context) -> None:
        self._gl = gl
        self._textures: Dict[TextureId, TextureHandle] = {}

        self._load_engine_defaults()

    def _load_engine_defaults(self) -> None:
        sky_data = generate_nishita_sky_lut(
            width=1024,
            height=512,
            sun_dir=(0.0, 1.0, 0.0),  # Default: Noon
        )

        self.create_from_bytes(
            TextureId("engine.sky_lut"),
            data=sky_data,
            width=1024,
            height=512,
            components=4,
            dtype="f4",
            label="Default Sky LUT",
        )

    def create_from_bytes(
        self,
        tex_id: TextureId,
        *,
        data: bytes,
        width: int,
        height: int,
        components: int,
        dtype: str,
        label: str = "",
    ) -> TextureHandle:
        if tex_id in self._textures:
            raise KeyError(f"Texture '{tex_id}' already exists")

        texture = self._gl.texture((width, height), components, data=data, dtype=dtype)

        if dtype == "f4":
            texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
            texture.repeat_x = False
            texture.repeat_y = False
        else:
            texture.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
            if components == 4:
                texture.build_mipmaps()

        handle = TextureHandle(texture=texture, label=label or str(tex_id))
        self._textures[tex_id] = handle
        return handle

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
        if tex_id in self._textures:
            raise KeyError(f"Texture '{tex_id}' already exists")

        texture = self._gl.texture((width, height), components, dtype=dtype)
        handle = TextureHandle(texture=texture, label=label or str(tex_id))
        self._textures[tex_id] = handle
        return handle

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
        if tex_id in self._textures:
            raise KeyError(f"Texture '{tex_id}' already exists")

        texture = self._gl.texture_cube((size, size), components, dtype=dtype)
        handle = TextureHandle(texture=texture, label=label or str(tex_id))
        self._textures[tex_id] = handle
        return handle

    def get(self, tex_id: TextureId) -> TextureHandle:
        """Retrieve an existing texture."""
        try:
            return self._textures[tex_id]
        except KeyError:
            raise KeyError(f"Texture '{tex_id}' not found")
