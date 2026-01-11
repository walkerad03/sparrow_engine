from typing import Any, Callable

import moderngl
import numpy as np

from sparrow.graphics.renderer.graph import RenderContext


class LightingPass:
    name = "lighting"

    def __init__(
        self,
        *,
        light_prog: moderngl.Program,
        light_vao: moderngl.VertexArray,
        set_uniform: Callable[[moderngl.Program, str, Any], None],
    ) -> None:
        self.prog = light_prog
        self.vao = light_vao
        self._set = set_uniform

    def execute(self, rc: RenderContext) -> None:
        ctx = rc.ctx

        # Bind lighting output framebuffer
        rc.frame.scene_fbo.use()
        ctx.clear(0.0, 0.0, 0.0, 1.0)

        # Additive blending (light accumulation)
        ctx.disable(moderngl.DEPTH_TEST)
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.ONE, moderngl.ONE

        # Bind Gbuffer Textures
        rc.frame.gbuffer.albedo.use(location=0)
        rc.frame.gbuffer.normal.use(location=1)
        rc.frame.gbuffer.depth.use(location=2)

        self._set(self.prog, "u_albedo", 0)
        self._set(self.prog, "u_normal", 1)
        self._set(self.prog, "u_depth", 2)

        # Camera uniforms
        inv_vp = np.linalg.inv(rc.camera.numpy_matrix)
        self._set(self.prog, "u_inv_view_proj", inv_vp.tobytes())
        self._set(self.prog, "u_view_proj", rc.camera.matrix)
        self._set(self.prog, "u_resolution", rc.ctx.viewport[2:4])

        # Accumulate lights
        for light in rc.draw_list.lights:
            self._set(self.prog, "u_light_pos", light.position)
            self._set(self.prog, "u_color", light.color)
            self._set(self.prog, "u_radius", light.radius)

            self.vao.render(mode=moderngl.TRIANGLE_STRIP)
