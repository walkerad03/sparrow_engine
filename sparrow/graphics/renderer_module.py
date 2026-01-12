from pathlib import Path
from typing import Any, cast

import moderngl
import pygame

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
from sparrow.graphics.renderer.passes.voxel import VoxelPass
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
            "gbuffer_mesh",
            ENGINE_SHADER_DIR / "gbuffer" / "mesh.vert",
            ENGINE_SHADER_DIR / "gbuffer" / "mesh.frag",
        )

        self.shaders.register_engine_shader(
            "voxelize",
            ENGINE_SHADER_DIR / "voxel" / "voxelize.vert",
            ENGINE_SHADER_DIR / "voxel" / "voxelize.frag",
            ENGINE_SHADER_DIR / "voxel" / "voxelize.geom",
        )

        self.shaders.register_engine_shader(
            "shadow",
            ENGINE_SHADER_DIR / "lighting" / "shadow.vert",
            ENGINE_SHADER_DIR / "lighting" / "shadow.frag",
        )

        self.shaders.register_engine_shader(
            "point_light",
            ENGINE_SHADER_DIR / "lighting" / "point_light.vert",
            ENGINE_SHADER_DIR / "lighting" / "point_light.frag",
        )

        self.shaders.register_engine_shader(
            "composite",
            ENGINE_SHADER_DIR / "post" / "fullscreen.vert",
            ENGINE_SHADER_DIR / "post" / "composite.frag",
        )

        self.textures: dict[str, Any] = {}
        self.get_texture("missing")

        self.default_normal = self.ctx.ctx.texture(
            (1, 1), 4, data=bytes([128, 128, 255, 255])
        )

        mesh_prog = self.shaders.get("gbuffer_mesh").program

        vox_res = (128, 128, 64)

        vox_albedo_occ = self.ctx.ctx.texture3d(vox_res, 4, dtype="u1")
        vox_albedo_occ.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        vox_albedo_occ.repeat_x = False
        vox_albedo_occ.repeat_y = False
        vox_albedo_occ.repeat_z = False

        vox_normal = self.ctx.ctx.texture3d(vox_res, 4, dtype="f2")
        vox_normal.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        vox_normal.repeat_x = False
        vox_normal.repeat_y = False
        vox_normal.repeat_z = False

        voxel_prog = self.shaders.get("voxelize").program

        shadow_prog = self.shaders.get("shadow").program

        light_prog = self.shaders.get("point_light").program
        light_vao = ctx.ctx.vertex_array(
            light_prog, [(ctx.quad_buffer, "2f 2f", "in_vert", "in_uv")]
        )

        composite_prog = self.shaders.get("composite").program
        composite_vao = ctx.ctx.vertex_array(
            composite_prog, [(ctx.quad_buffer, "2f 2f", "in_vert", "in_uv")]
        )

        scene_tex = ctx.ctx.texture(ctx.logical_res, 4)
        scene_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        scene_fbo = ctx.ctx.framebuffer(color_attachments=[scene_tex])

        self.render_graph = RenderGraph()
        self.render_graph.add_pass(
            GBufferPass(
                mesh_prog=mesh_prog,
                set_uniform=self._set,
                get_texture=self.get_texture,
            )
        )

        self.render_graph.add_pass(
            VoxelPass(
                prog=voxel_prog,
                set_uniform=self._set,
                get_texture=self.get_texture,
                world_size=(512.0, 512.0, 256.0),
            )
        )

        self.render_graph.add_pass(
            LightingPass(
                light_prog=light_prog,
                light_vao=light_vao,
                shadow_prog=shadow_prog,
                set_uniform=self._set,
            )
        )

        self.render_graph.add_pass(
            PostProcessPass(
                composite_prog=composite_prog,
                composite_vao=composite_vao,
                set_uniform=self._set,
            )
        )

        self.frame = FrameResources(
            gbuffer=self.gbuffer,
            scene_fbo=scene_fbo,
            vox_albedo_occ=vox_albedo_occ,
            vox_normal=vox_normal,
            vox_res=vox_res,
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

        self.render_graph.execute(rc)
        self.ctx.flip()
