from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

import moderngl
import numpy as np

from sparrow.core.components import transform_to_matrix
from sparrow.graphics.renderer.graph import RenderContext


@dataclass
class PointShadow:
    size: int
    tex_face: List[moderngl.Texture]  # 6x R32F
    fbos: List[moderngl.Framebuffer]  # 6x FBO (color=tex, depth=rb)
    depth_rbs: List[moderngl.Renderbuffer]  # shared depth renderbuffer


class LightingPass:
    name = "lighting"

    def __init__(
        self,
        *,
        light_prog: moderngl.Program,
        light_vao: moderngl.VertexArray,
        shadow_prog: moderngl.Program,
        set_uniform: Callable[[moderngl.Program, str, Any], None],
    ) -> None:
        self.prog = light_prog
        self.vao = light_vao
        self.shadow_prog = shadow_prog
        self._set = set_uniform

        self._shadow_maps: Dict[int, PointShadow] = {}
        self._shadow_vao_cache: Dict[Tuple[int, int], moderngl.VertexArray] = {}

    def _get_point_shadow(
        self, ctx: moderngl.Context, light_eid: int, size: int = 256
    ) -> PointShadow:
        sm = self._shadow_maps.get(light_eid)
        if sm is not None and sm.size == size:
            return sm

        tex_faces: List[moderngl.Texture] = []
        fbos: List[moderngl.Framebuffer] = []
        depth_rbs: List[moderngl.Renderbuffer] = []

        for _ in range(6):
            t = ctx.texture((size, size), components=1, dtype="f4")
            t.filter = (moderngl.NEAREST, moderngl.NEAREST)
            t.repeat_x = False
            t.repeat_y = False
            depth_rb = ctx.depth_renderbuffer((size, size))
            depth_rbs.append(depth_rb)
            fbos.append(
                ctx.framebuffer(color_attachments=[t], depth_attachment=depth_rb)
            )
            tex_faces.append(t)

        sm = PointShadow(size=size, tex_face=tex_faces, fbos=fbos, depth_rbs=depth_rbs)
        self._shadow_maps[light_eid] = sm
        return sm

    def _render_point_shadows(self, rc: RenderContext, light, sm: PointShadow) -> None:
        ctx = rc.ctx

        DIRS = np.array(
            [
                [1, 0, 0],
                [-1, 0, 0],
                [0, 1, 0],
                [0, -1, 0],
                [0, 0, 1],
                [0, 0, -1],
            ],
            dtype="f4",
        )

        UPS = np.array(
            [
                [0, -1, 0],
                [0, -1, 0],
                [0, 0, 1],
                [0, 0, -1],
                [0, -1, 0],
                [0, -1, 0],
            ],
            dtype="f4",
        )

        def look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
            f = target - eye
            f = f / np.linalg.norm(f)
            u = up / np.linalg.norm(up)
            s = np.cross(f, u)
            s = s / np.linalg.norm(s)
            u = np.cross(s, f)

            m = np.eye(4, dtype="f4")
            m[0, :3] = s
            m[1, :3] = u
            m[2, :3] = -f
            t = np.eye(4, dtype="f4")
            t[:3, 3] = -eye
            return m @ t

        def perspective(
            fov_deg: float, aspect: float, znear: float, zfar: float
        ) -> np.ndarray:
            fov = np.deg2rad(fov_deg)
            f = 1.0 / np.tan(fov / 2.0)
            m = np.zeros((4, 4), dtype="f4")
            m[0, 0] = f / aspect
            m[1, 1] = f
            m[2, 2] = (zfar + znear) / (znear - zfar)
            m[2, 3] = (2 * zfar * znear) / (znear - zfar)
            m[3, 2] = -1.0
            return m

        ctx.enable(moderngl.DEPTH_TEST)
        ctx.disable(moderngl.BLEND | moderngl.CULL_FACE)
        ctx.viewport = (0, 0, sm.size, sm.size)

        lp = np.array(light.position, dtype="f4")
        far_ = float(light.radius)
        proj = perspective(90.0, 1.0, 0.1, far_)

        self._set(self.shadow_prog, "u_light_pos", tuple(light.position))
        self._set(self.shadow_prog, "u_shadow_far", far_)

        for face in range(6):
            sm.fbos[face].use()
            sm.fbos[face].clear(1.0, 1.0, 1.0, 1.0, depth=1.0)

            view = look_at(lp, lp + DIRS[face], UPS[face])
            vp = proj @ view
            self._set(self.shadow_prog, "u_light_view_proj", vp.tobytes())

            for item in rc.draw_list.transparent:
                renderable = item.renderable
                mesh = rc.meshes.get(renderable.mesh_id)

                vao_key = (self.shadow_prog.glo, mesh.vbo.glo)
                vao = self._shadow_vao_cache.get(vao_key)
                if not vao:
                    vao = ctx.vertex_array(
                        self.shadow_prog,
                        [(mesh.vbo, mesh.layout[0], *mesh.attribs)],
                    )
                    self._shadow_vao_cache[vao_key] = vao

                model = transform_to_matrix(item.position, item.rotation, item.scale)
                self._set(self.shadow_prog, "u_model", model.tobytes())

                vc = mesh.vertex_count
                assert vc is not None
                vao.render(mode=mesh.mode, vertices=vc)

                if face == 0:
                    data = sm.tex_face[0].read()
                    arr = np.frombuffer(data, dtype=np.float32)
                    print(
                        "shadow0 min/max after face0:",
                        float(arr.min()),
                        float(arr.max()),
                    )

        rc.frame.scene_fbo.use()

        w, h = rc.frame.scene_fbo.size
        ctx.viewport = (0, 0, w, h)

        ctx.disable(moderngl.DEPTH_TEST)
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.ONE, moderngl.ONE

    def execute(self, rc: RenderContext) -> None:
        ctx = rc.ctx

        # Bind lighting output framebuffer
        rc.frame.scene_fbo.use()
        w, h = rc.frame.scene_fbo.size
        ctx.viewport = (0, 0, w, h)
        ctx.clear(0.0, 0.0, 0.0, 1.0)

        # Additive blending (light accumulation)
        ctx.disable(moderngl.DEPTH_TEST)
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.ONE, moderngl.ONE

        # Bind Gbuffer Textures
        rc.frame.gbuffer.albedo.use(location=0)
        rc.frame.gbuffer.normal.use(location=1)
        rc.frame.gbuffer.depth.use(location=2)
        rc.frame.vox_albedo_occ.use(location=3)
        rc.frame.vox_normal.use(location=4)

        self._set(self.prog, "u_shadow_bias", 0.05)

        # Camera uniforms
        inv_vp = np.linalg.inv(rc.camera.numpy_matrix)
        self._set(self.prog, "u_inv_view_proj", inv_vp.tobytes())
        self._set(self.prog, "u_view_proj", rc.camera.matrix)
        self._set(self.prog, "u_resolution", rc.ctx.viewport[2:4])

        # voxel AABB + resolution
        center = np.array(rc.camera.current_target, dtype="f4")
        world_size = np.array((512.0, 512.0, 256.0), dtype="f4")
        half = world_size * 0.5
        vox_min = center - half
        vox_max = center + half
        self._set(self.prog, "u_vox_min", tuple(vox_min.tolist()))
        self._set(self.prog, "u_vox_max", tuple(vox_max.tolist()))
        self._set(self.prog, "u_vox_res", rc.frame.vox_res)

        # Accumulate lights
        for light in rc.draw_list.lights:
            sm = self._get_point_shadow(ctx, light.eid, size=256)
            self._render_point_shadows(rc, light, sm)

            for i in range(6):
                sm.tex_face[i].use(location=5 + i)

            self._set(self.prog, "u_light_pos", light.position)
            self._set(self.prog, "u_color", light.color)
            self._set(self.prog, "u_radius", light.radius)
            self._set(self.prog, "u_shadow_far", light.radius)

            self.vao.render(mode=moderngl.TRIANGLE_STRIP)
