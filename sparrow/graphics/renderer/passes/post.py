from typing import Any, Callable

import moderngl

from sparrow.graphics.renderer.graph import RenderContext


class PostProcessPass:
    name = "post"

    def __init__(
        self,
        *,
        composite_prog: moderngl.Program,
        composite_vao: moderngl.VertexArray,
        set_uniform: Callable[[moderngl.Program, str, Any], None],
    ) -> None:
        self.prog = composite_prog
        self.vao = composite_vao
        self._set = set_uniform

    def execute(self, rc: RenderContext) -> None:
        ctx = rc.ctx

        # output to screen
        ctx.screen.use()
        ctx.clear(0.0, 0.0, 0.0, 1.0)

        ctx.disable(moderngl.DEPTH_TEST)
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.ONE, moderngl.ZERO

        # Bind textures
        rc.frame.gbuffer.albedo.use(0)
        rc.frame.scene_fbo.color_attachments[0].use(1)

        self._set(self.prog, "u_diffuse", 0)
        self._set(self.prog, "u_lighting", 1)

        self.vao.render(mode=moderngl.TRIANGLE_STRIP)
