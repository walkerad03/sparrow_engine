from pathlib import Path
from typing import Any, cast

import moderngl
import pygame

from sparrow.core.components import Sprite, Transform
from sparrow.core.world import World
from sparrow.graphics.camera import Camera
from sparrow.graphics.context import GraphicsContext
from sparrow.graphics.gbuffer import GBuffer
from sparrow.graphics.light import BlocksLight, PointLight
from sparrow.graphics.shaders import ShaderManager


class Renderer:
    def __init__(self, ctx: GraphicsContext, asset_path: Path):
        self.ctx = ctx
        self.asset_path = asset_path

        self.gbuffer = GBuffer(ctx.ctx, ctx.logical_res)
        self.shaders = ShaderManager(ctx.ctx, asset_path)
        self.camera = Camera(ctx.logical_res)

        self.textures: dict[str, Any] = {}
        self.get_texture("missing")

        self.default_normal = self.ctx.ctx.texture(
            (1, 1), 4, data=bytes([128, 128, 255, 255])
        )

        # 1. Sprite Pass VAO
        self.sprite_prog = self.shaders.get("sprite")
        self.sprite_vao = ctx.ctx.vertex_array(
            self.sprite_prog, [(ctx.quad_buffer, "2f 2f", "in_vert", "in_uv")]
        )

        # 2. Lighting Pass VAO
        self.light_prog = self.shaders.get("point_light")
        self.light_vao = ctx.ctx.vertex_array(
            self.light_prog, [(ctx.quad_buffer, "2f 2f", "in_vert", "in_uv")]
        )

        self.ambient_prog = self.shaders.get_bespoke(
            "ambient", "fullscreen.vert", "ambient.frag"
        )
        self.ambient_vao = ctx.ctx.vertex_array(
            self.ambient_prog, [(ctx.quad_buffer, "2f 2f", "in_vert", "in_uv")]
        )

        self.bloom_res = (ctx.logical_res[0] // 2, ctx.logical_res[1] // 2)
        self.bloom_tex_1 = ctx.ctx.texture(self.bloom_res, 4)
        self.bloom_tex_2 = ctx.ctx.texture(self.bloom_res, 4)
        self.bloom_tex_1.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.bloom_tex_2.filter = (moderngl.LINEAR, moderngl.LINEAR)

        self.bloom_fbo_1 = ctx.ctx.framebuffer(color_attachments=[self.bloom_tex_1])
        self.bloom_fbo_2 = ctx.ctx.framebuffer(color_attachments=[self.bloom_tex_2])

        self.blur_prog = self.shaders.get_bespoke(
            "blur", "fullscreen.vert", "blur.frag"
        )
        self.blur_vao = ctx.ctx.vertex_array(
            self.blur_prog, [(ctx.quad_buffer, "2f 2f", "in_vert", "in_uv")]
        )

        self.scene_tex = ctx.ctx.texture(ctx.logical_res, 4)
        self.scene_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.scene_fbo = ctx.ctx.framebuffer(color_attachments=[self.scene_tex])

    def _set(self, prog: moderngl.Program, name: str, value: Any) -> None:
        """Safely sets a uniform value if it exists."""
        if name in prog:
            uniform = cast(moderngl.Uniform, prog[name])

            if isinstance(value, bytes):
                uniform.write(value)
            else:
                uniform.value = value

    def get_texture(self, name: str):
        if name in self.textures:
            return self.textures[name]

        path = self.asset_path.parent / "textures" / f"{name}.png"

        if not path.exists():
            print(f"[WARN] Texture '{name}' not found. Trying 'missing.png'.")
            path = self.asset_path.parent / "textures" / "missing.png"

            if not path.exists():
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
        self._set(self.sprite_prog, "u_matrix", self.camera.matrix)

        for eid, sprite, trans in world.join(Sprite, Transform):
            assert isinstance(sprite, Sprite) and isinstance(trans, Transform)
            tex = self.get_texture(sprite.texture_id)
            tex.use(location=0)
            self._set(self.sprite_prog, "u_texture", 0)

            if sprite.normal_map_id:
                norm = self.get_texture(sprite.normal_map_id)
                norm.use(location=1)
            else:
                self.default_normal.use(location=1)
            self._set(self.sprite_prog, "u_normal_map", 1)

            tex_w, tex_h = tex.size

            rx, ry, rw, rh = sprite.region if sprite.region else (0.0, 0.0, 1.0, 1.0)

            scale_x, scale_y = trans.scale

            final_w: float = tex_w * scale_x * rw
            final_h: float = tex_h * scale_y * rh

            # Per-Instance Uniforms
            self._set(self.sprite_prog, "u_pos", (trans.x, trans.y))
            self._set(self.sprite_prog, "u_size", (final_w, final_h))
            self._set(self.sprite_prog, "u_rot", trans.rotation)
            self._set(self.sprite_prog, "u_pivot", sprite.pivot)
            self._set(self.sprite_prog, "u_region", (rx, ry, rw, rh))
            self._set(self.sprite_prog, "u_skew", sprite.skew)

            if world.has(eid, BlocksLight):
                self._set(self.sprite_prog, "u_blocks_light", 1.0)
            else:
                self._set(self.sprite_prog, "u_blocks_light", 0.0)

            self._set(self.sprite_prog, "u_color", sprite.color)
            self._set(self.sprite_prog, "u_layer", sprite.layer / 10.0)

            # Draw
            self.sprite_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # 2. LIGHTING PASS (Draw to Screen)
        self.scene_fbo.use()
        self.ctx.ctx.clear(0.0, 0.0, 0.0, 1.0)

        self.ctx.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.ctx.enable(moderngl.BLEND)
        self.ctx.ctx.blend_func = moderngl.ONE, moderngl.ONE
        self.gbuffer.occlusion.use(location=0)
        self.gbuffer.albedo.use(location=1)
        self.gbuffer.normal.use(location=2)

        self._set(self.light_prog, "u_occlusion", 0)
        self._set(self.light_prog, "u_albedo", 1)
        self._set(self.light_prog, "u_normal", 2)

        self._set(self.light_prog, "u_matrix", self.camera.matrix)
        self._set(self.light_prog, "u_resolution", self.ctx.logical_res)

        for _, light, trans in world.join(PointLight, Transform):
            assert isinstance(light, PointLight) and isinstance(trans, Transform)
            self._set(self.light_prog, "u_light_pos", (trans.x, trans.y))

            c = light.color
            if len(c) == 3:
                c = (c[0], c[1], c[2], 1.0)
            self._set(self.light_prog, "u_color", c)
            self._set(self.light_prog, "u_radius", light.radius)

            # Quad Size Optimization
            self._set(self.light_prog, "u_pos", (trans.x, trans.y))
            size = light.radius * 2.2
            self._set(self.light_prog, "u_size", (size, size))

            # Draw
            self.light_vao.render(mode=moderngl.TRIANGLE_STRIP)

        self.ctx.ctx.disable(moderngl.BLEND)

        self.bloom_fbo_1.use()
        self.scene_tex.use(location=0)  # Read from sharp scene
        self._set(self.blur_prog, "u_texture", 0)
        self._set(self.blur_prog, "u_resolution", self.bloom_res)
        self._set(self.blur_prog, "u_direction", (1.0, 0.0))  # Horizontal
        self.blur_vao.render(mode=moderngl.TRIANGLE_STRIP)

        self.bloom_fbo_2.use()
        self.bloom_tex_1.use(location=0)  # Read from Pass 1
        self._set(self.blur_prog, "u_texture", 0)
        self._set(self.blur_prog, "u_direction", (0.0, 1.0))  # Vertical
        self.blur_vao.render(mode=moderngl.TRIANGLE_STRIP)

        self.ctx.ctx.screen.use()
        self.ctx.clear()
        self.ctx.ctx.enable(moderngl.BLEND)

        self.ctx.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.gbuffer.albedo.use(location=0)
        self._set(self.ambient_prog, "u_albedo", 0)
        self._set(self.ambient_prog, "u_color", (0.1, 0.1, 0.2, 1.0))
        self.ambient_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # A. Draw Sharp Scene
        self.ctx.ctx.blend_func = moderngl.ONE, moderngl.ONE
        self.scene_tex.use(location=0)
        self._set(self.ambient_prog, "u_albedo", 0)
        self._set(self.ambient_prog, "u_color", (1.0, 1.0, 1.0, 1.0))
        self.ambient_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # B. Draw Bloom (Additive)
        self.ctx.ctx.blend_func = moderngl.ONE, moderngl.ONE  # Add glow on top
        self.bloom_tex_2.use(location=0)
        self._set(self.ambient_prog, "u_albedo", 0)
        self._set(
            self.ambient_prog, "u_color", (0.25, 0.25, 0.25, 1.0)
        )  # Glow intensity
        self.ambient_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # 3. POST-PROCESS / FLIP
        self.ctx.flip()
