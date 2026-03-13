# sparrow/graphics/passes/forward.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import moderngl

from sparrow.assets import AssetHandle, AssetServer, DefaultShaders
from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
    RenderServices,
)
from sparrow.graphics.resources import ShaderManager
from sparrow.graphics.utils import pack_mat4
from sparrow.graphics.utils.batcher import RenderBatcher
from sparrow.graphics.utils.ids import ResourceId
from sparrow.graphics.utils.uniforms import set_uniform


@dataclass
class ForwardPBRPass(RenderPass):
    """
    Standard Forward Rendering Pass.
    Draws all opaque objects in the RenderFrame.
    """

    target: Optional[ResourceId] = None

    _batcher: RenderBatcher | None = None
    _vs_handle: AssetHandle | None = None
    _fs_handle: AssetHandle | None = None

    _asset_server: AssetServer | None = None
    _shader_manager: ShaderManager | None = None

    def build(self) -> PassBuildInfo:
        writes = [PassResourceUse(self.target, "write")] if self.target else []
        return PassBuildInfo(pass_id=self.pass_id, reads=[], writes=writes)

    def on_compile(
        self, ctx: moderngl.Context, services: RenderServices
    ) -> None:
        self._batcher = RenderBatcher(ctx)
        self._shader_manager = services.shader_manager
        self._asset_server = services.gpu_resources.asset_server

        assert self._asset_server
        self._vs_handle = self._asset_server.load(DefaultShaders.FORWARD_VS)
        self._fs_handle = self._asset_server.load(DefaultShaders.FORWARD_FS)

    def on_destroy(self) -> None:
        if self._batcher:
            self._batcher.release()
            self._batcher = None

    def execute(self, ctx: PassExecutionContext) -> None:
        assert (
            self._shader_manager
            and self._asset_server
            and self._vs_handle
            and self._fs_handle
            and self._batcher
        )

        program = self._shader_manager.get_program_from_assets(
            self._asset_server, self._vs_handle, self._fs_handle
        )

        if not program:
            return

        gl = ctx.gl

        if self.target:
            ctx.graph_resources[self.target].use()
        else:
            gl.screen.use()

        gl.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)

        # TODO: Use UBOs
        set_uniform(
            program,
            "u_view_proj",
            pack_mat4(ctx.frame.camera.view_proj.T),
        )
        set_uniform(program, "u_has_albedo_tex", 0)

        if ctx.frame.mesh_ids.size > 0:
            batches = self._batcher.group_columns(
                ctx.frame.mesh_ids, ctx.frame.albedo_ids
            )

            for (mesh_id, albedo_id), indices in batches.items():
                gpu_mesh = ctx.gpu_resources.get_mesh(mesh_id)
                if not gpu_mesh:
                    continue

                has_albedo_tex = 0
                if albedo_id is not None:
                    gpu_tex = ctx.gpu_resources.get_texture(albedo_id)
                    if gpu_tex:
                        gpu_tex.use(0)
                        set_uniform(program, "u_albedo_tex", 0)
                        has_albedo_tex = 1

                set_uniform(program, "u_has_albedo_tex", has_albedo_tex)

                self._batcher.prepare_instance_data_columns(
                    indices,
                    ctx.frame.transforms,
                    ctx.frame.colors,
                    ctx.frame.roughness,
                    ctx.frame.metallic,
                    ctx.frame.emissive,
                )

                vao = gpu_mesh.get_instanced_vao(program, self._batcher.buffer)
                vao.render(instances=int(indices.size))
        else:
            batches = self._batcher.group_objects(ctx.frame.objects)

            for (mesh_id, albedo_id), instances in batches.items():
                gpu_mesh = ctx.gpu_resources.get_mesh(mesh_id)
                if not gpu_mesh:
                    continue

                has_albedo_tex = 0
                if albedo_id is not None:
                    gpu_tex = ctx.gpu_resources.get_texture(albedo_id)
                    if gpu_tex:
                        gpu_tex.use(0)
                        set_uniform(program, "u_albedo_tex", 0)
                        has_albedo_tex = 1

                set_uniform(program, "u_has_albedo_tex", has_albedo_tex)

                self._batcher.prepare_instance_data(
                    instances, ctx.frame.transforms
                )

                vao = gpu_mesh.get_instanced_vao(program, self._batcher.buffer)
                vao.render(instances=len(instances))
