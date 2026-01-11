from pathlib import Path
from typing import Any, cast

import moderngl
import pygame
from moderngl import VertexArray

import sparrow.graphics.shaders as shader_pkg
from sparrow.core.world import World
from sparrow.graphics.assets.materials import MaterialLibrary
from sparrow.graphics.assets.meshes import MeshLibrary
from sparrow.graphics.assets.shaders import ShaderLibrary
from sparrow.graphics.camera import Camera3D
from sparrow.graphics.context import GraphicsContext
from sparrow.graphics.gbuffer import GBuffer
from sparrow.graphics.renderer.draw_list import RenderDrawList
from sparrow.graphics.renderer.frame import FrameResources
from sparrow.graphics.renderer.graph import RenderContext, RenderGraph
from sparrow.graphics.renderer.passes.gbuffer import GBufferPass
from sparrow.graphics.renderer.passes.lighting import LightingPass
from sparrow.graphics.renderer.passes.post import PostProcessPass
from sparrow.graphics.systems.build_draw_list import build_draw_list_system
from sparrow.graphics.systems.sprite_to_renderable import sprite_to_renderable_system


class Renderer:
    def __init__(self, ctx: GraphicsContext, asset_path: Path):
        self.ctx = ctx
        self.asset_path = asset_path

        ENGINE_SHADER_DIR = Path(str(shader_pkg.__file__)).resolve().parent

        self.gbuffer = GBuffer(ctx.ctx, ctx.logical_res)
        self.camera = Camera3D(ctx.logical_res)
        self.shaders = ShaderLibrary(ctx.ctx)
        self.materials = MaterialLibrary()
        self.meshes = MeshLibrary(ctx.ctx)

        self.shaders.register_engine_shader(
            "gbuffer_sprite",
            ENGINE_SHADER_DIR / "gbuffer" / "sprite.vert",
            ENGINE_SHADER_DIR / "gbuffer" / "sprite.frag",
        )

        self.shaders.register_engine_shader(
            "gbuffer_mesh",
            ENGINE_SHADER_DIR / "gbuffer" / "mesh.vert",
            ENGINE_SHADER_DIR / "gbuffer" / "mesh.frag",
        )

        self.shaders.register_engine_shader(
            "point_light",
            ENGINE_SHADER_DIR / "lighting" / "point_light.vert",
            ENGINE_SHADER_DIR / "lighting" / "point_light.frag",
        )

        self.shaders.register_engine_shader(
            "ambient",
            ENGINE_SHADER_DIR / "post" / "fullscreen.vert",
            ENGINE_SHADER_DIR / "lighting" / "ambient.frag",
        )

        self.shaders.register_engine_shader(
            "blur",
            ENGINE_SHADER_DIR / "post" / "fullscreen.vert",
            ENGINE_SHADER_DIR / "post" / "blur.frag",
        )

        self.textures: dict[str, Any] = {}
        self.get_texture("missing")

        self.default_normal = self.ctx.ctx.texture(
            (1, 1), 4, data=bytes([128, 128, 255, 255])
        )

        self.sprite_prog = self.shaders.get("gbuffer_sprite").program
        self.sprite_vao = ctx.ctx.vertex_array(
            self.sprite_prog, [(ctx.quad_buffer, "2f 2f", "in_vert", "in_uv")]
        )

        self.mesh_prog = self.shaders.get("gbuffer_mesh").program

        self.light_prog = self.shaders.get("point_light").program
        self.light_vao = ctx.ctx.vertex_array(
            self.light_prog, [(ctx.quad_buffer, "2f 2f", "in_vert", "in_uv")]
        )

        self.ambient_prog = self.shaders.get("ambient").program
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

        self.blur_prog = self.shaders.get("blur").program
        self.blur_vao = ctx.ctx.vertex_array(
            self.blur_prog, [(ctx.quad_buffer, "2f 2f", "in_vert", "in_uv")]
        )

        self.scene_tex = ctx.ctx.texture(ctx.logical_res, 4)
        self.scene_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.scene_fbo = ctx.ctx.framebuffer(color_attachments=[self.scene_tex])

        self.render_graph = RenderGraph()
        self.render_graph.add_pass(
            GBufferPass(
                mesh_prog=self.mesh_prog,
                set_uniform=self._set,
                get_texture=self.get_texture,
            )
        )
        """
        self.render_graph.add_pass(
            LightingPass(
                light_prog=self.light_prog,
                light_vao=self.light_vao,
                set_uniform=self._set,
            )
        )

        self.render_graph.add_pass(
            PostProcessPass(
                blur_prog=self.blur_prog,
                blur_vao=self.blur_vao,
                ambient_prog=self.ambient_prog,
                ambient_vao=self.ambient_vao,
                set_uniform=self._set,
                bloom_res=self.bloom_res,
            )
        )
        """
        self.frame = FrameResources(
            gbuffer=self.gbuffer,
            scene_fbo=self.scene_fbo,
            bloom_fbo_1=self.bloom_fbo_1,
            bloom_fbo_2=self.bloom_fbo_2,
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

        path = self.asset_path / "textures" / f"{name}.png"

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

    def render(self, world: World) -> None:
        sprite_to_renderable_system(world)
        build_draw_list_system(world)

        draw_list = world.try_resource(RenderDrawList)
        if not draw_list:
            return

        rc = RenderContext(
            ctx=self.ctx.ctx,
            camera=self.camera,
            shaders=self.shaders,
            materials=self.materials,
            meshes=self.meshes,
            frame=self.frame,
            draw_list=draw_list,
        )

        # import numpy as np

        # dl = draw_list.transparent or draw_list.opaque
        # if dl:
        #    p = dl[0].position
        #    self.camera.current_target[:] = np.array([p.x, p.y, p.z], dtype="f4")
        #    self.camera._dirty = True

        self.render_graph.execute(rc)
        self.ctx.flip()
