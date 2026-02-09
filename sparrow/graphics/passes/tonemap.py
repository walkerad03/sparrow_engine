# sparrow/graphics/passes/tonemap.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import moderngl

from sparrow.assets import AssetHandle, AssetServer, DefaultShaders
from sparrow.graphics.graph import (
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
    RenderServices,
)
from sparrow.graphics.resources import ShaderManager
from sparrow.graphics.utils import create_fullscreen_triangle
from sparrow.graphics.utils.ids import ResourceId
from sparrow.graphics.utils.uniforms import set_uniform


@dataclass
class TonemapPass(RenderPass):
    """
    Post-Processing Pass: Reads an HDR texture, applies Reinhard Tonemapping,
    Gamma Correction, and outputs to the Screen (or target).
    """

    input_texture: ResourceId
    target: Optional[ResourceId] = None

    _vs_handle: AssetHandle | None = None
    _fs_handle: AssetHandle | None = None

    _asset_server: AssetServer | None = None
    _shader_manager: ShaderManager | None = None

    _triangle_buffer: moderngl.Buffer | None = None
    _vao: moderngl.VertexArray | None = None

    def build(self) -> PassBuildInfo:
        reads = [PassResourceUse(self.input_texture, "read")]
        writes = [PassResourceUse(self.target, "write")] if self.target else []
        return PassBuildInfo(pass_id=self.pass_id, reads=reads, writes=writes)

    def on_compile(
        self, ctx: moderngl.Context, services: RenderServices
    ) -> None:
        self._shader_manager = services.shader_manager
        self._asset_server = services.gpu_resources.asset_server

        self._vs_handle = self._asset_server.load(DefaultShaders.TONEMAP_VS)
        self._fs_handle = self._asset_server.load(DefaultShaders.TONEMAP_FS)

        self._triangle_buffer = create_fullscreen_triangle(ctx)

    def on_destroy(self) -> None:
        if self._vao:
            self._vao.release()
            self._vao = None
        if self._triangle_buffer:
            self._triangle_buffer.release()
            self._triangle_buffer = None

    def execute(self, ctx: PassExecutionContext) -> None:
        assert (
            self._shader_manager
            and self._asset_server
            and self._vs_handle
            and self._fs_handle
            and self._triangle_buffer
        )

        program = self._shader_manager.get_program_from_assets(
            self._asset_server, self._vs_handle, self._fs_handle
        )
        if not program:
            return

        if not self._vao:
            self._vao = ctx.gl.vertex_array(
                program, [(self._triangle_buffer, "2f", "in_pos")]
            )

        if self.target:
            ctx.graph_resources[self.target].use()
        else:
            ctx.gl.screen.use()

        ctx.gl.disable(moderngl.DEPTH_TEST)

        hdr_texture = ctx.graph_resources[self.input_texture]
        hdr_texture.use(location=0)
        set_uniform(program, "u_texture", 0)

        self._vao.render(mode=moderngl.TRIANGLES)
