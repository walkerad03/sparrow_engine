# sparrow/graphics/resources/texture.py
import moderngl

from sparrow.assets.types import TextureData


class GPUTexture:
    """
    Wrapper around moderngl.Texture.
    """

    def __init__(self, ctx: moderngl.Context, data: TextureData):
        self._ctx = ctx
        self.width = data.width
        self.height = data.height

        # Create Texture
        self.handle = ctx.texture(
            size=(data.width, data.height),
            components=data.components,
            data=data.data,
        )

        # Default Settings (can be overridden by Material)
        self.handle.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        self.handle.build_mipmaps()
        self.handle.anisotropy = 16.0

    def use(self, location: int = 0) -> None:
        self.handle.use(location)

    def release(self) -> None:
        self.handle.release()
