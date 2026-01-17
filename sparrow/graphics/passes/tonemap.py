# sparrow/graphics/passes/tonemap.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import moderngl

from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassExecutionContext,
    PassFeatures,
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
from sparrow.graphics.renderer.settings import RendererSettings
from sparrow.graphics.shaders.program_types import ShaderStages
from sparrow.graphics.shaders.shader_manager import ShaderRequest
from sparrow.graphics.util.ids import PassId, ResourceId, ShaderId


@dataclass(kw_only=True)
class TonemapPass(RenderPass):
    """
    Trivial fullscreen blit pass.

    Reads:
      - HDR input texture

    Writes:
      - default framebuffer
    """

    pass_id: PassId
    settings: RendererSettings

    hdr_in: ResourceId

    features: PassFeatures = PassFeatures.RESOLUTION

    _vao: moderngl.VertexArray | None = None
    _vbo: moderngl.Buffer | None = None

    @property
    def output_target(self) -> None:
        return None  # screen

    def build(self) -> PassBuildInfo:
        return PassBuildInfo(
            pass_id=self.pass_id,
            name="Tonemap",
            reads=[PassResourceUse(self.hdr_in, "read", "sampled", 0)],
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
            shader_id=ShaderId("tonemap"),
            stages=ShaderStages(
                vertex="sparrow/graphics/shaders/default/tonemap.vert",
                fragment="sparrow/graphics/shaders/default/tonemap.frag",
            ),
            label="Tonemap",
        )

        program = services.shader_manager.get(req).program
        if not isinstance(program, moderngl.Program):
            raise RuntimeError("TonemapPass requires a graphics Program")

        self._set_sampler("u_hdr", 0)

        vbo = create_fullscreen_triangle(ctx)
        vao = ctx.vertex_array(program, [(vbo, "2f", "in_pos")])

        self._program = program
        super().on_graph_compiled(ctx=ctx, resources=resources, services=services)

        self._vao = vao
        self._vbo = vbo

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        self.execute_base(exec_ctx)

        assert self._vao
        assert isinstance(self._program, moderngl.Program)

        gl = exec_ctx.gl
        gl.screen.use()

        # bind default framebuffer viewport
        gl.disable(moderngl.CULL_FACE | moderngl.DEPTH_TEST | moderngl.BLEND)
        gl.viewport = (0, 0, exec_ctx.viewport_width, exec_ctx.viewport_height)
        gl.clear()

        # bind HDR input
        tex = expect_resource(exec_ctx.resources, self.hdr_in, TextureResource)
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
