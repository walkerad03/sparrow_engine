# sparrow/graphics/passes/forward_tonemap.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, cast

import moderngl

from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
    RenderServices,
)
from sparrow.graphics.graph.resources import (
    GraphResource,
    TextureResource,
    expect_resource,
)
from sparrow.graphics.helpers.fullscreen import create_fullscreen_triangle
from sparrow.graphics.shaders.program_types import ShaderStages
from sparrow.graphics.shaders.shader_manager import ShaderRequest
from sparrow.graphics.util.ids import PassId, ResourceId, ShaderId


@dataclass(slots=True)
class ForwardTonemapPass(RenderPass):
    pass_id: PassId
    hdr_input: ResourceId

    _program: moderngl.Program | None = None
    _vao: moderngl.VertexArray | None = None
    _u_hdr: moderngl.Uniform | None = None

    def build(self) -> PassBuildInfo:
        return PassBuildInfo(
            pass_id=self.pass_id,
            name="Forward Tonemap",
            reads=[
                PassResourceUse(
                    resource=self.hdr_input,
                    access="read",
                    stage="color",
                    binding=0,
                )
            ],
            writes=[],
        )

    def on_graph_compiled(
        self,
        *,
        ctx: moderngl.Context,
        resources: Mapping[ResourceId, GraphResource[object]],
        services: RenderServices,
    ) -> None:
        req = ShaderRequest(
            shader_id=ShaderId("forward_tonemap"),
            stages=ShaderStages(
                vertex="sparrow/graphics/shaders/default/tonemap_fullscreen.vert",
                fragment="sparrow/graphics/shaders/default/tonemap.frag",
            ),
            label="ForwardTonemap",
        )

        prog_handle = services.shader_manager.get(req)
        program = cast(moderngl.Program, prog_handle.program)

        vbo = create_fullscreen_triangle(ctx)
        vao = ctx.vertex_array(program, [(vbo, "2f", "in_pos")])

        self._program = program
        self._vao = vao
        self._u_hdr = cast(moderngl.Uniform, program["u_hdr"])

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        assert self._program is not None
        assert self._vao is not None
        assert self._u_hdr is not None

        gl = exec_ctx.gl

        gl.screen.use()
        gl.viewport = (0, 0, exec_ctx.viewport_width, exec_ctx.viewport_height)

        gl.disable(moderngl.DEPTH_TEST | moderngl.BLEND | moderngl.CULL_FACE)

        hdr_tex = expect_resource(exec_ctx.resources, self.hdr_input, TextureResource)
        hdr_tex.handle.use(0)
        self._u_hdr.value = 0

        self._vao.render(mode=moderngl.TRIANGLES)

    def on_graph_destroyed(self) -> None:
        self._program = None
        self._vao = None
        self._u_hdr = None
