# sparrow/graphics/passes/blit.py
from dataclasses import dataclass

import moderngl

from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
)
from sparrow.graphics.graph.resources import TextureResource, expect_resource
from sparrow.graphics.helpers.fullscreen import create_fullscreen_triangle
from sparrow.graphics.shaders.program_types import ShaderStages
from sparrow.graphics.shaders.shader_manager import ShaderRequest
from sparrow.graphics.util.ids import ResourceId, ShaderId, TextureId


@dataclass(kw_only=True)
class BlitPass(RenderPass):
    """
    A simple pass that copies a texture to the screen (or output target).
    """

    texture_id: TextureId

    _program: moderngl.Program | None = None
    _vao: moderngl.VertexArray | None = None
    _vbo: moderngl.Buffer | None = None

    def build(self) -> PassBuildInfo:
        return PassBuildInfo(
            pass_id=self.pass_id,
            name="Blit Pass",
            reads=[],
            writes=[],
        )

    def on_graph_compiled(
        self, *, ctx: moderngl.Context, resources, services
    ) -> None:
        req = ShaderRequest(
            shader_id=ShaderId("blit"),
            stages=ShaderStages(
                vertex="sparrow/graphics/shaders/default/blit.vert",
                fragment="sparrow/graphics/shaders/default/blit.frag",
            ),
            label="BlitShader",
        )
        self._program = services.shader_manager.get(req).program

        self._vbo = create_fullscreen_triangle(ctx)
        self._vao = ctx.vertex_array(
            self._program, [(self._vbo, "2f", "in_pos")]
        )

        self._uniforms["u_texture"] = self._program["u_texture"]

        super().on_graph_compiled(
            ctx=ctx, resources=resources, services=services
        )

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        if not self._program:
            return

        self.execute_base(exec_ctx)
        gl = exec_ctx.gl

        gl.screen.use()

        tex_id = self.texture_id
        tex_handle = exec_ctx.services.texture_manager.get(tex_id)
        tex_handle.texture.use(location=0)
        self._uniforms["u_texture"].value = 0

        w, h = exec_ctx.viewport_width, exec_ctx.viewport_height
        gl.viewport = (0, 0, w, h)
        gl.disable(moderngl.DEPTH_TEST)

        assert self._vao
        self._vao.render(moderngl.TRIANGLES)

    def on_graph_destroyed(self) -> None:
        self._program = None
        if self._vao:
            self._vao.release()
        if self._vbo:
            self._vbo.release()
