import pygame
from pathlib import Path
from typing import Any, cast

import moderngl

from sparrow.core.components import Sprite, Transform
from sparrow.core.world import World
from sparrow.graphics.camera import Camera
from sparrow.graphics.context import GraphicsContext
from sparrow.graphics.gbuffer import GBuffer
from sparrow.graphics.light import PointLight, BlocksLight
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
            tex = self.get_texture(sprite.texture_id)
            tex.use(location=0)
            self._set(self.sprite_prog, "u_texture", 0)

            # Per-Instance Uniforms
            self._set(self.sprite_prog, "u_pos", (trans.x, trans.y))

            w, h = 16.0 * trans.scale, 16.0 * trans.scale
            self._set(self.sprite_prog, "u_size", (w, h))
            self._set(self.sprite_prog, "u_rot", trans.rotation)

            if world.has(eid, BlocksLight):
                self._set(self.sprite_prog, "u_blocks_light", 1.0)
            else:
                self._set(self.sprite_prog, "u_blocks_light", 0.0)

            self._set(self.sprite_prog, "u_color", sprite.color)
            self._set(self.sprite_prog, "u_layer", sprite.layer / 10.0)

            # Draw
            self.sprite_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # 2. LIGHTING PASS (Draw to Screen)
        self.ctx.ctx.screen.use()
        self.ctx.clear()

        self.ctx.ctx.enable(moderngl.BLEND)
        self.ctx.ctx.blend_func = moderngl.ONE, moderngl.ONE
        self.ctx.ctx.disable(moderngl.DEPTH_TEST)

        self.gbuffer.occlusion.use(location=0)
        self.gbuffer.albedo.use(location=1)

        self._set(self.light_prog, "u_occlusion", 0)
        self._set(self.light_prog, "u_albedo", 1)

        self._set(self.light_prog, "u_matrix", self.camera.matrix)
        self._set(self.light_prog, "u_resolution", self.ctx.logical_res)

        for _, light, trans in world.join(PointLight, Transform):
            self._set(self.light_prog, "u_light_pos", (trans.x, trans.y))

            c = light.color
            if len(c) == 3:
                c = (c[0], c[1], c[2], 1.0)
            self._set(self.light_prog, "u_color", c)
            self._set(self.light_prog, "u_radius", light.radius)

            # Quad Size Optimization
            self._set(self.light_prog, "u_pos", (trans.x, trans.y))
            diameter = light.radius * 2.0
            self._set(self.light_prog, "u_size", (diameter, diameter))

            # Draw
            self.light_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # 3. POST-PROCESS / FLIP
        self.ctx.flip()

    def render_debug(self, world: World):
        """Debugs the Occlusion Map by drawing it directly to the screen."""
        self.ctx.ctx.screen.use()
        self.ctx.clear()
        self.ctx.ctx.disable(moderngl.DEPTH_TEST)

        # 1. Geometry Pass (We still need to fill the G-Buffer!)
        self.gbuffer.use()
        self.ctx.ctx.clear(0.0, 0.0, 0.0)
        self._set(self.sprite_prog, "u_matrix", self.camera.matrix)

        for eid, sprite, trans in world.join(Sprite, Transform):
            # ... Copy your normal Geometry Pass loop here ...
            tex = self.get_texture(sprite.texture_id)
            tex.use(location=0)
            self._set(self.sprite_prog, "u_texture", 0)

            # Ensure u_is_solid logic is active!
            if world.has(eid, BlocksLight):
                self._set(self.sprite_prog, "u_blocks_light", 1.0)
            else:
                self._set(self.sprite_prog, "u_blocks_light", 0.0)

            self._set(self.sprite_prog, "u_pos", (trans.x, trans.y))
            w, h = 16.0 * trans.scale, 16.0 * trans.scale
            self._set(self.sprite_prog, "u_size", (w, h))
            self._set(self.sprite_prog, "u_rot", trans.rotation)
            self._set(self.sprite_prog, "u_color", sprite.color)
            self._set(self.sprite_prog, "u_layer", sprite.layer / 10.0)
            self.sprite_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # 2. DEBUG BLIT (Draw Occlusion to Screen)
        self.ctx.ctx.screen.use()

        if not hasattr(self, "debug_prog"):
            # Create a simple full-screen quad shader on the fly
            self.debug_prog = self.ctx.ctx.program(
                vertex_shader="""
                    #version 330 core
                    layout (location=0) in vec2 in_vert;
                    layout (location=1) in vec2 in_uv;
                    out vec2 v_uv;
                    void main() {
                        v_uv = in_uv;
                        // Quad is 0..1, map to -1..1
                        gl_Position = vec4(in_vert * 2.0 - 1.0, 0.0, 1.0); 
                    }
                """,
                fragment_shader="""
                    #version 330 core
                    in vec2 v_uv;
                    uniform sampler2D u_tex;
                    out vec4 f_color;
                    void main() {
                        // Visualize Red Channel (Occlusion) as White
                        float c = texture(u_tex, v_uv).r;
                        f_color = vec4(c, c, c, 1.0);
                    }
                """,
            )

        # Bind Occlusion Texture to Unit 0
        self.gbuffer.occlusion.use(location=0)
        self.debug_prog["u_tex"].value = 0

        # Reuse light_vao (it's just a quad)
        self.light_vao.render(mode=moderngl.TRIANGLE_STRIP)

        self.ctx.flip()
