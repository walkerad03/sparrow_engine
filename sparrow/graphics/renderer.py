import pygame
from pathlib import Path
from typing import Any, cast

import moderngl

from sparrow.core.components import Sprite, Transform
from sparrow.core.world import World
from sparrow.graphics.camera import Camera
from sparrow.graphics.context import GraphicsContext
from sparrow.graphics.gbuffer import GBuffer
from sparrow.graphics.light import AmbientLight, PointLight
from sparrow.graphics.shaders import ShaderManager


class Renderer:
    def __init__(self, ctx: GraphicsContext, asset_path: Path):
        self.ctx = ctx
        self.asset_path = asset_path

        self.gbuffer = GBuffer(ctx.ctx, ctx.logical_res)
        self.shaders = ShaderManager(ctx.ctx, asset_path)
        self.camera = Camera(ctx.logical_res)

        # 1. Sprite Pass VAO
        self.sprite_prog = self.shaders.get("sprite")
        self.sprite_vao = ctx.ctx.vertex_array(
            self.sprite_prog, [(ctx.quad_buffer, "2f 2f", "in_vert", "in_uv")]
        )

        # 2. Lighting Pass VAO
        self.light_prog = self.shaders.get("lighting")
        self.light_vao = ctx.ctx.vertex_array(
            self.light_prog, [(ctx.quad_buffer, "2f 2f", "in_vert", "in_uv")]
        )

        # 3. Post/Quad Pass VAO
        self.post_prog = self.shaders.get("post")
        self.post_vao = ctx.ctx.vertex_array(
            self.post_prog, [(ctx.quad_buffer, "2f 2f", "in_vert", "in_uv")]
        )

        self.textures: dict[str, Any] = {}
        self.get_texture("missing")

    def _set(self, prog: moderngl.Program, name: str, value: Any) -> None:
        """Safely sets a uniform value if it exists."""
        if name in prog:
            # Cast to Uniform to satisfy linter that .value exists
            cast(moderngl.Uniform, prog[name]).value = value

    def _write(self, prog: moderngl.Program, name: str, data: bytes) -> None:
        """Safely writes raw bytes to a uniform if it exists."""
        if name in prog:
            # Cast to Uniform to satisfy linter that .write() exists
            cast(moderngl.Uniform, prog[name]).write(data)

    def get_texture(self, name: str):
        if name in self.textures:
            return self.textures[name]

        path = self.asset_path.parent / "textures" / f"{name}.png"

        if not path.exists():
            print(f"[WARN] Texture '{name}' not found. Trying 'missing.png'.")
            path = self.asset_path.parent / "textures" / "missing.png"

            if not path.exists():
                print("[ERR] 'missing.png' not found! Generating fallback.")
                tex = self.ctx.ctx.texture((1, 1), 4, data=b"\xff\x00\xff\xff")
                tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
                self.textures[name] = tex
                return tex

        img = pygame.image.load(path).convert_alpha()
        data = pygame.image.tobytes(img, "RGBA", True)
        tex = self.ctx.ctx.texture(img.get_size(), 4, data=data)

        tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        tex.swizzle = "RGBA"

        self.textures[name] = tex
        return tex

    def render(self, world: World):
        """
        Main Render Loop.
        """

        # 1. GEOMETRY PASS (Fill the G-Buffer)
        self.gbuffer.use()
        self.ctx.ctx.clear(0.0, 0.0, 0.0, 0.0)

        self.ctx.ctx.enable(moderngl.BLEND)
        self.ctx.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.ctx.ctx.enable(moderngl.DEPTH_TEST)

        # Global Uniforms
        self._write(self.sprite_prog, "u_matrix", self.camera.matrix)

        for _, sprite, trans in world.join(Sprite, Transform):
            tex = self.get_texture(sprite.texture_id)
            tex.use(location=0)

            self._set(self.sprite_prog, "u_texture", 0)

            # Per-Instance Uniforms
            self._set(self.sprite_prog, "u_pos", (trans.x, trans.y))

            w, h = 16.0 * trans.scale, 16.0 * trans.scale
            self._set(self.sprite_prog, "u_size", (w, h))
            self._set(self.sprite_prog, "u_rot", trans.rotation)
            self._set(self.sprite_prog, "u_color", sprite.color)
            self._set(self.sprite_prog, "u_layer", sprite.layer / 10.0)

            # Draw
            self.sprite_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # 2. LIGHTING PASS (Draw to Screen)
        self.ctx.ctx.screen.use()
        self.ctx.clear()

        self.gbuffer.bind_textures(start_slot=0)

        # Samplers (0=Albedo, 1=Normal, 2=Occlusion)
        self._set(self.light_prog, "u_albedo", 0)
        self._set(self.light_prog, "u_normal", 1)
        self._set(self.light_prog, "u_occlusion", 2)

        self._write(self.light_prog, "u_matrix", self.camera.matrix)

        # --- 2a. Ambient Light ---
        ambient_color = (0.02, 0.02, 0.05)
        for _, amb in world.join(AmbientLight):
            ambient_color = amb.color
            break

        self._set(self.light_prog, "u_ambient", ambient_color)

        # --- 2b. Point Lights ---
        self.ctx.ctx.enable(moderngl.BLEND)
        self.ctx.ctx.blend_func = moderngl.ONE, moderngl.ONE
        self.ctx.ctx.disable(moderngl.DEPTH_TEST)

        for eid, light, trans in world.join(PointLight, Transform):
            self._set(self.light_prog, "u_light_pos", (trans.x, trans.y))
            self._set(self.light_prog, "u_light_color", light.color)
            self._set(self.light_prog, "u_light_radius", light.radius)
            self._set(self.light_prog, "u_intensity", light.intensity)
            self._set(self.light_prog, "u_cast_shadows", light.cast_shadows)

            # Quad Size Optimization
            self._set(self.light_prog, "u_pos", (trans.x, trans.y))
            size = light.radius * 2.2
            self._set(self.light_prog, "u_size", (size, size))

            # Draw
            self.light_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # 3. POST-PROCESS / FLIP
        self.ctx.flip()
