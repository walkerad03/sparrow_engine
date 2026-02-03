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
            ctx.frame.camera.view_proj.T.tobytes(),
        )

        batches = self._batcher.group_objects(ctx.frame.objects)

        for mesh_id, instances in batches.items():
            gpu_mesh = ctx.gpu_resources.get_mesh(mesh_id)
            if not gpu_mesh:
                continue

            self._batcher.prepare_instance_data(instances)

            vao = gpu_mesh.get_instanced_vao(program, self._batcher.buffer)
            vao.render(instances=len(instances))
