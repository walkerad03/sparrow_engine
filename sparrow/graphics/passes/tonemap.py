# sparrow/graphics/passes/tonemap.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple, cast

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
class TonemapPass(RenderPass):
    """
    Trivial fullscreen blit pass.

    Reads:
      - HDR input texture

    Writes:
      - default framebuffer
    """

    pass_id: PassId
    hdr_input: ResourceId
    clear_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    _program: moderngl.Program | moderngl.ComputeShader | None = None
    _vao: moderngl.VertexArray | None = None
    _vbo: moderngl.Buffer | None = None

    def build(self) -> PassBuildInfo:
        return PassBuildInfo(
            pass_id=self.pass_id,
            name="Tonemap",
            reads=[
                PassResourceUse(
                    resource=self.hdr_input,
                    access="read",
                    stage="sampled",
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
        shader_mgr = services.shader_manager

        req = ShaderRequest(
            shader_id=ShaderId("tonemap"),
            stages=ShaderStages(
                vertex="sparrow/graphics/shaders/default/tonemap.vert",
                fragment="sparrow/graphics/shaders/default/tonemap.frag",
            ),
            label="Tonemap",
        )

        prog_handle = shader_mgr.get(req)
        program = prog_handle.program

        u = cast(moderngl.Uniform, program["u_hdr"])
        try:
            u.value = 0
        except KeyError:
            pass

        vbo = create_fullscreen_triangle(ctx)
        vao = ctx.vertex_array(program, [(vbo, "2f", "in_pos")])

        self._program = program
        self._vao = vao
        self._vbo = vbo

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        assert self._vao
        assert self._program

        gl = exec_ctx.gl
        gl.screen.use()

        # bind default framebuffer viewport
        gl.disable(moderngl.CULL_FACE)
        gl.disable(moderngl.DEPTH_TEST)
        gl.disable(moderngl.BLEND)
        gl.viewport = (0, 0, exec_ctx.viewport_width, exec_ctx.viewport_height)

        # clear default framebuffer
        gl.clear(
            red=self.clear_color[0],
            green=self.clear_color[1],
            blue=self.clear_color[2],
            alpha=self.clear_color[3],
        )

        # bind HDR input
        tex = expect_resource(exec_ctx.resources, self.hdr_input, TextureResource)
        tex.handle.use(location=0)

        # draw to default framebuffer
        self._vao.render(mode=moderngl.TRIANGLES, vertices=3)

    def on_graph_destroyed(self) -> None:
        if self._vao is not None:
            self._vao.release()
        if self._vbo is not None:
            self._vbo.release()
        self._vao = None
        self._vbo = None
        self._program = None
