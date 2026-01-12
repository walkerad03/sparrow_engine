from typing import Any, Callable

import moderngl

from sparrow.core.components import transform_to_matrix
from sparrow.graphics.renderer.graph import RenderContext


class GBufferPass:
    name = "gbuffer"

    def __init__(
        self,
        *,
        mesh_prog: moderngl.Program,
        set_uniform: Callable[[moderngl.Program, str, Any], None],
        get_texture: Callable[[str], Any],
    ) -> None:
        self.mesh_prog = mesh_prog
        self._set = set_uniform
        self.get_texture = get_texture

    def execute(self, rc: RenderContext):
        ctx = rc.ctx

        rc.frame.gbuffer.use()

        ctx.clear(0.0, 0.0, 0.2, 0.0, 1.0)

        ctx.enable(moderngl.BLEND | moderngl.DEPTH_TEST)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        # Global Uniforms
        self._set(self.mesh_prog, "u_view_proj", rc.camera.matrix)

        draw_list = rc.draw_list

        for _, item in enumerate(draw_list.transparent):
            renderable = item.renderable

            mesh = rc.meshes.get(renderable.mesh_id)

            vao = rc.ctx.vertex_array(
                self.mesh_prog,
                [(mesh.vbo, mesh.layout[0], *mesh.attribs)],
            )

            # Build and load model matrix
            model = transform_to_matrix(item.position, item.rotation, item.scale)
            self._set(self.mesh_prog, "u_model", model.tobytes())

            # Diffuse material
            tex = self.get_texture(renderable.material)
            tex.use(location=0)
            self._set(self.mesh_prog, "u_albedo", 0)

            assert mesh.vertex_count is not None
            vao.render(mode=mesh.mode, vertices=mesh.vertex_count)

        rc.frame.gbuffer.generate_mipmaps()
