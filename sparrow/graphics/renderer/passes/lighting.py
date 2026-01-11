from typing import Any, Callable

import moderngl
import numpy as np

from sparrow.core.components import Transform
from sparrow.core.world import World
from sparrow.graphics.light import PointLight
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
        self.light_prog = light_prog
        self.light_vao = light_vao
        self._set = set_uniform

    def execute(self, rc: RenderContext, world: World) -> None:
        # Bind lighting output framebuffer
        rc.frame.scene_fbo.use()
        rc.ctx.clear(0.0, 0.0, 0.0, 1.0)

        # Additive blending (light accumulation)
        rc.ctx.disable(moderngl.DEPTH_TEST)
        rc.ctx.enable(moderngl.BLEND)
        rc.ctx.blend_func = moderngl.ONE, moderngl.ONE

        # Bind Gbuffer Textures
        rc.frame.gbuffer.occlusion.use(location=0)
        rc.frame.gbuffer.albedo.use(location=1)
        rc.frame.gbuffer.normal.use(location=2)
        rc.frame.gbuffer.depth.use(location=3)

        self._set(self.light_prog, "u_occlusion", 0)
        self._set(self.light_prog, "u_albedo", 1)
        self._set(self.light_prog, "u_normal", 2)
        self._set(self.light_prog, "u_depth", 3)

        # Camera uniforms
        self._set(self.light_prog, "u_matrix", rc.camera.matrix)
        self._set(self.light_prog, "u_resolution", rc.ctx.viewport[2:4])

        inv_matrix = np.linalg.inv(rc.camera.numpy_matrix)
        self._set(self.light_prog, "u_inv_matrix", inv_matrix.tobytes())

        # Accumulate lights
        for _, light, trans in world.join(PointLight, Transform):
            assert isinstance(light, PointLight) and isinstance(trans, Transform)
            self._set(self.light_prog, "u_light_pos", trans.pos)

            color = light.color
            if len(color) == 3:
                color = (color[0], color[1], color[2], 1.0)
            self._set(self.light_prog, "u_color", color)
            self._set(self.light_prog, "u_radius", light.radius)

            # Quad bounds optimization
            size = light.radius * 2.2
            self._set(self.light_prog, "u_pos", trans.pos)
            self._set(self.light_prog, "u_size", (size, size))

            self.light_vao.render(mode=moderngl.TRIANGLE_STRIP)
