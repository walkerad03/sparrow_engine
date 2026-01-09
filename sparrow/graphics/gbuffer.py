from typing import Tuple

import moderngl


class GBuffer:
    def __init__(self, ctx: moderngl.Context, resolution: Tuple[int, int]):
        self.ctx = ctx
        self.width, self.height = resolution

        # Texture 1: Albedo (RGB) + Specular/Emission (Alpha)
        self.albedo = self.ctx.texture((self.width, self.height), 4)
        self.albedo.filter = (moderngl.NEAREST, moderngl.NEAREST)

        # Texture 2: Normal Map (RGB) + Depth/Height (Alpha)
        # Using float16 for precision in lighting calculations
        self.normal = self.ctx.texture((self.width, self.height), 4, dtype="f2")
        self.normal.filter = (moderngl.NEAREST, moderngl.NEAREST)

        # Texture 3: Occlusion (Mask for raycasting shadows)
        self.occlusion = self.ctx.texture((self.width, self.height), 1)
        self.occlusion.filter = (moderngl.NEAREST, moderngl.NEAREST)

        # The Framebuffer that bundles them together
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.albedo, self.normal, self.occlusion],
            depth_attachment=self.ctx.depth_renderbuffer((self.width, self.height)),
        )

    def use(self):
        """Bind this buffer for writing (Geometry Pass)."""
        self.fbo.use()
        self.fbo.clear()

    def bind_textures(self, start_slot: int = 0):
        """Bind textures for reading (Lighting Pass)."""
        self.albedo.use(location=start_slot)
        self.normal.use(location=start_slot + 1)
        self.occlusion.use(location=start_slot + 2)
