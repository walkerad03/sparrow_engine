from typing import Any, Callable

import moderngl

from sparrow.core.world import World
from sparrow.graphics.renderer.graph import RenderContext


class PostProcessPass:
    name = "post"

    def __init__(
        self,
        *,
        blur_prog: moderngl.Program,
        blur_vao: moderngl.VertexArray,
        ambient_prog: moderngl.Program,
        ambient_vao: moderngl.VertexArray,
        set_uniform: Callable[[moderngl.Program, str, Any], None],
        bloom_res: tuple[int, int],
    ) -> None:
        self.blur_prog = blur_prog
        self.blur_vao = blur_vao
        self.ambient_prog = ambient_prog
        self.ambient_vao = ambient_vao
        self._set = set_uniform
        self.bloom_res = bloom_res

    def execute(self, rc: RenderContext, world: World) -> None:
        # Horizontal bloom blur pass
        rc.ctx.disable(moderngl.BLEND)

        rc.frame.bloom_fbo_1.use()
        rc.frame.scene_fbo.color_attachments[0].use(location=0)

        self._set(self.blur_prog, "u_texture", 0)
        self._set(self.blur_prog, "u_resolution", self.bloom_res)
        self._set(self.blur_prog, "u_direction", (1.0, 0.0))

        self.blur_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # Vertical bloom blur pass

        rc.frame.bloom_fbo_2.use()
        rc.frame.bloom_fbo_1.color_attachments[0].use(location=0)

        self._set(self.blur_prog, "u_texture", 0)
        self._set(self.blur_prog, "u_direction", (0.0, 1.0))

        self.blur_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # Final composite to screen
        rc.ctx.screen.use()
        rc.ctx.clear()

        rc.ctx.enable(moderngl.BLEND)

        # Composite ambient base
        rc.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        rc.frame.gbuffer.albedo.use(location=0)
        self._set(self.ambient_prog, "u_albedo", 0)
        self._set(self.ambient_prog, "u_color", (0.1, 0.1, 0.2, 1.0))

        self.ambient_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # Composite sharp lit scene
        rc.ctx.blend_func = moderngl.ONE, moderngl.ONE

        rc.frame.scene_fbo.color_attachments[0].use(location=0)
        self._set(self.ambient_prog, "u_albedo", 0)
        self._set(self.ambient_prog, "u_color", (1.0, 1.0, 1.0, 1.0))

        self.ambient_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # Composite bloom
        rc.frame.bloom_fbo_2.color_attachments[0].use(location=0)
        self._set(self.ambient_prog, "u_albedo", 0)
        self._set(self.ambient_prog, "u_color", (0.25, 0.25, 0.25, 1.0))

        self.ambient_vao.render(mode=moderngl.TRIANGLE_STRIP)
