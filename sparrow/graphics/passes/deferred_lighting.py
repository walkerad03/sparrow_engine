# sparrow/graphics/passes/deferred_lighting.py
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Mapping, Sequence

import moderngl
import numpy as np

from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
    RenderServices,
)
from sparrow.graphics.graph.resources import (
    FramebufferResource,
    GraphResource,
    TextureResource,
    expect_resource,
)
from sparrow.graphics.helpers.fullscreen import create_fullscreen_triangle
from sparrow.graphics.shaders.program_types import ShaderStages
from sparrow.graphics.shaders.shader_manager import ShaderRequest
from sparrow.graphics.util.ids import PassId, ResourceId, ShaderId


def _pack_vec4_array(
    values: Sequence[tuple[float, float, float, float]], *, max_len: int
) -> bytes:
    """
    Pack a list of vec4 into tightly packed float32 bytes, padded to max_len.

    Args:
        values: Vec4 tuples.
        max_len: Fixed array length expected by shader.

    Returns:
        Bytes suitable for moderngl.Uniform.write().
    """
    out = bytearray()
    n = min(len(values), max_len)
    for i in range(n):
        x, y, z, w = values[i]
        out += struct.pack("4f", float(x), float(y), float(z), float(w))
    # pad remaining
    for _ in range(max_len - n):
        out += struct.pack("4f", 0.0, 0.0, 0.0, 0.0)
    return bytes(out)


@dataclass(slots=True)
class DeferredLightingPass(RenderPass):
    """
    Full-screen deferred lighting.

    Reads:
        - GBuffer textures (albedo, normal, orm, depth)
    Writes:
        - light_accum texture (hdr)
    """

    pass_id: PassId
    out_fbo: ResourceId
    light_accum: ResourceId
    g_albedo: ResourceId
    g_normal: ResourceId
    g_orm: ResourceId
    g_depth: ResourceId

    _program: moderngl.Program | None = None
    _vao: moderngl.VertexArray | None = None
    _fs_vbo: moderngl.Buffer | None = None

    _u_inv_view_proj: moderngl.Uniform | None = None
    _u_camera_pos: moderngl.Uniform | None = None

    _u_light_count: moderngl.Uniform | None = None
    _u_light_pos_radius: moderngl.Uniform | None = None
    _u_light_color_intensity: moderngl.Uniform | None = None

    _max_lights: int = 64

    def build(self) -> PassBuildInfo:
        return PassBuildInfo(
            pass_id=self.pass_id,
            name="Deferred Lighting",
            reads=[
                PassResourceUse(self.g_albedo, "read", "texture", 0),
                PassResourceUse(self.g_normal, "read", "texture", 1),
                PassResourceUse(self.g_orm, "read", "texture", 2),
                PassResourceUse(self.g_depth, "read", "texture", 3),
            ],
            writes=[
                PassResourceUse(self.light_accum, "write", "color", 0),
            ],
        )

    def on_graph_compiled(
        self,
        *,
        ctx: moderngl.Context,
        resources: Mapping[ResourceId, GraphResource[object]],
        services: RenderServices,
    ) -> None:
        """Compile fullscreen lighting shader; setup uniform blocks for light lists if desired."""
        shader_mgr = services.shader_manager

        req = ShaderRequest(
            shader_id=ShaderId("deferred_lighting"),
            stages=ShaderStages(
                vertex="sparrow/graphics/shaders/default/deferred_lighting.vert",
                fragment="sparrow/graphics/shaders/default/deferred_lighting_pbr.frag",
            ),
            label="DeferredLighting",
        )

        prog = shader_mgr.get(req).program
        if not isinstance(prog, moderngl.Program):
            raise RuntimeError(
                "DeferredLightingPass requires a graphics Program, not ComputeShader"
            )

        # Create fullscreen triangle geometry
        vbo = create_fullscreen_triangle(ctx)
        vao = ctx.vertex_array(prog, [(vbo, "2f", "in_pos")])

        # Cache uniforms with explicit type asserts to satisfy type checkers/stubs
        u_inv_view_proj = prog.get("u_inv_view_proj", None)
        u_camera_pos = prog.get("u_camera_pos", None)

        u_light_count = prog.get("u_light_count", None)
        u_light_pos_radius = prog.get("u_light_pos_radius", None)
        u_light_color_intensity = prog.get("u_light_color_intensity", None)

        u_g_albedo = prog.get("u_g_albedo", None)
        u_g_normal = prog.get("u_g_normal", None)
        u_g_orm = prog.get("u_g_orm", None)
        u_g_depth = prog.get("u_g_depth", None)

        if not isinstance(u_inv_view_proj, moderngl.Uniform):
            raise RuntimeError("Missing uniform u_inv_view_proj")
        if not isinstance(u_camera_pos, moderngl.Uniform):
            raise RuntimeError("Missing uniform u_camera_pos")

        if not isinstance(u_light_count, moderngl.Uniform):
            raise RuntimeError("Missing uniform u_light_count")
        if not isinstance(u_light_pos_radius, moderngl.Uniform):
            raise RuntimeError("Missing uniform u_light_pos_radius")
        if not isinstance(u_light_color_intensity, moderngl.Uniform):
            raise RuntimeError("Missing uniform u_light_color_intensity")

        if not isinstance(u_g_albedo, moderngl.Uniform):
            raise RuntimeError("Missing uniform u_g_albedo")
        if not isinstance(u_g_normal, moderngl.Uniform):
            raise RuntimeError("Missing uniform u_g_normal")
        if not isinstance(u_g_orm, moderngl.Uniform):
            raise RuntimeError("Missing uniform u_g_orm")
        if not isinstance(u_g_depth, moderngl.Uniform):
            raise RuntimeError("Missing uniform u_g_depth")

        # Bind sampler locations (avoid Literal typing issues by forcing int())
        u_g_albedo.value = int(0)
        u_g_normal.value = int(1)
        u_g_orm.value = int(2)
        u_g_depth.value = int(3)
        # Store
        self._program = prog
        self._vao = vao
        self._fs_vbo = vbo

        self._u_inv_view_proj = u_inv_view_proj
        self._u_camera_pos = u_camera_pos

        self._u_light_count = u_light_count
        self._u_light_pos_radius = u_light_pos_radius
        self._u_light_color_intensity = u_light_color_intensity

        self._u_g_albedo = u_g_albedo
        self._u_g_normal = u_g_normal
        self._u_g_orm = u_g_orm
        self._u_g_depth = u_g_depth

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        """Bind GBuffer textures and render a fullscreen triangle."""
        gl = exec_ctx.gl

        # Resolve output framebuffer
        out_fbo_res = expect_resource(
            exec_ctx.resources,
            ResourceId(f"fbo:{self.pass_id}"),
            FramebufferResource,
        )
        out_fbo = out_fbo_res.handle
        out_fbo.use()

        # Ensure viewport matches internal target
        gl.viewport = (0, 0, out_fbo.size[0], out_fbo.size[1])

        # State: lighting pass is screen-space
        gl.disable(moderngl.DEPTH_TEST)
        gl.disable(moderngl.CULL_FACE)
        gl.clear(0.0, 0.0, 0.0, 1.0)

        # Resolve inputs
        albedo_res = expect_resource(exec_ctx.resources, self.g_albedo, TextureResource)
        normal_res = expect_resource(exec_ctx.resources, self.g_normal, TextureResource)
        orm_res = expect_resource(exec_ctx.resources, self.g_orm, TextureResource)
        depth_res = expect_resource(exec_ctx.resources, self.g_depth, TextureResource)

        # Bind textures to fixed units
        albedo_res.handle.use(location=0)
        normal_res.handle.use(location=1)
        orm_res.handle.use(location=2)
        depth_res.handle.use(location=3)

        # Program + uniforms
        if self._program is None or self._vao is None:
            raise RuntimeError("DeferredLightingPass not compiled")

        assert self._u_inv_view_proj is not None
        assert self._u_camera_pos is not None
        assert self._u_light_count is not None
        assert self._u_light_pos_radius is not None
        assert self._u_light_color_intensity is not None

        cam = exec_ctx.frame.camera

        # inv(view_proj)
        inv_vp = np.linalg.inv(cam.view_proj).astype(np.float32, copy=False)
        self._u_inv_view_proj.write(inv_vp.T.tobytes())

        # camera pos
        cam_pos = cam.position_ws.astype(np.float32, copy=False)
        self._u_camera_pos.value = (
            float(cam_pos[0]),
            float(cam_pos[1]),
            float(cam_pos[2]),
        )

        # point lights (pack into vec4 arrays)
        lights = exec_ctx.frame.point_lights
        light_count = min(len(lights), self._max_lights)
        self._u_light_count.value = int(light_count)

        pos_radius: list[tuple[float, float, float, float]] = []
        col_int: list[tuple[float, float, float, float]] = []

        for i in range(light_count):
            lp = lights[i]
            px, py, pz = (
                float(lp.position_ws[0]),
                float(lp.position_ws[1]),
                float(lp.position_ws[2]),
            )
            pos_radius.append((px, py, pz, float(lp.radius)))

            cr, cg, cb = (
                float(lp.color_rgb[0]),
                float(lp.color_rgb[1]),
                float(lp.color_rgb[2]),
            )
            col_int.append((cr, cg, cb, float(lp.intensity)))

        self._u_light_pos_radius.write(
            _pack_vec4_array(pos_radius, max_len=self._max_lights)
        )
        self._u_light_color_intensity.write(
            _pack_vec4_array(col_int, max_len=self._max_lights)
        )

        # Draw
        self._vao.render(mode=moderngl.TRIANGLES)

    def on_graph_destroyed(self) -> None:
        if self._vao is not None:
            self._vao.release()
        if self._fs_vbo is not None:
            self._fs_vbo.release()

        self._program = None
        self._vao = None
        self._fs_vbo = None

        self._u_inv_view_proj = None
        self._u_camera_pos = None
        self._u_light_count = None
        self._u_light_pos_radius = None
        self._u_light_color_intensity = None

        self._u_g_albedo = None
        self._u_g_normal = None
        self._u_g_orm = None
        self._u_g_depth = None
