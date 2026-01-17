# sparrow/graphics/passes/deferred_lighting.py
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Mapping, Sequence

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
    FramebufferResource,
    GraphResource,
    TextureResource,
    expect_resource,
)
from sparrow.graphics.helpers.fullscreen import create_fullscreen_triangle
from sparrow.graphics.renderer.settings import DeferredRendererSettings
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


@dataclass(kw_only=True)
class DeferredLightingPass(RenderPass):
    """
    Full-screen deferred lighting.

    Reads:
        - GBuffer textures (albedo, normal, orm, depth)
    Writes:
        - light_accum texture (hdr)
    """

    pass_id: PassId
    settings: DeferredRendererSettings

    light_accum: ResourceId
    g_albedo: ResourceId
    g_normal: ResourceId
    g_orm: ResourceId
    g_depth: ResourceId

    features: PassFeatures = PassFeatures.CAMERA | PassFeatures.SUN

    _vao: moderngl.VertexArray | None = None
    _fs_vbo: moderngl.Buffer | None = None

    _u_light_count: moderngl.Uniform | None = None
    _u_light_pos_radius: moderngl.Uniform | None = None
    _u_light_color_intensity: moderngl.Uniform | None = None

    _max_lights: int = 64

    @property
    def output_target(self) -> ResourceId | None:
        return self.light_accum

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
        req = ShaderRequest(
            shader_id=ShaderId("deferred_lighting"),
            stages=ShaderStages(
                vertex="sparrow/graphics/shaders/default/deferred_lighting.vert",
                fragment="sparrow/graphics/shaders/default/deferred_lighting_pbr.frag",
            ),
            label="DeferredLighting",
        )

        prog = services.shader_manager.get(req).program
        if not isinstance(prog, moderngl.Program):
            raise RuntimeError("DeferredLightingPass requires a graphics Program")

        # Create fullscreen triangle geometry
        vbo = create_fullscreen_triangle(ctx)
        vao = ctx.vertex_array(prog, [(vbo, "2f", "in_pos")])

        # Cache uniforms with explicit type asserts to satisfy type checkers/stubs
        u_light_count = prog.get("u_light_count", None)
        u_light_pos_radius = prog.get("u_light_pos_radius", None)
        u_light_color_intensity = prog.get("u_light_color_intensity", None)
        if not isinstance(u_light_count, moderngl.Uniform):
            raise RuntimeError("Missing uniform u_light_count")
        if not isinstance(u_light_pos_radius, moderngl.Uniform):
            raise RuntimeError("Missing uniform u_light_pos_radius")
        if not isinstance(u_light_color_intensity, moderngl.Uniform):
            raise RuntimeError("Missing uniform u_light_color_intensity")

        for name in ["u_g_albedo", "u_g_normal", "u_g_orm", "u_g_depth"]:
            if name not in prog or not isinstance(prog[name], moderngl.Uniform):
                raise RuntimeError(f"Missing uniform {name}")

        # Bind sampler locations (avoid Literal typing issues by forcing int())
        self._set_sampler("u_g_albedo", 0)
        self._set_sampler("u_g_normal", 1)
        self._set_sampler("u_g_orm", 2)
        self._set_sampler("u_g_depth", 3)

        # Store
        self._program = prog
        super().on_graph_compiled(ctx=ctx, resources=resources, services=services)

        self._vao = vao
        self._fs_vbo = vbo

        self._u_light_count = u_light_count
        self._u_light_pos_radius = u_light_pos_radius
        self._u_light_color_intensity = u_light_color_intensity

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        self.execute_base(exec_ctx)

        gl = exec_ctx.gl

        # Resolve output framebuffer
        out_fbo_res = expect_resource(
            exec_ctx.resources,
            self.output_fbo_id,
            FramebufferResource,
        )
        out_fbo = out_fbo_res.handle
        out_fbo.use()

        # Ensure viewport matches internal target
        gl.viewport = (0, 0, out_fbo.size[0], out_fbo.size[1])

        # State: lighting pass is screen-space
        gl.disable(moderngl.DEPTH_TEST | moderngl.CULL_FACE | moderngl.BLEND)
        gl.clear(0.0, 0.0, 0.0, 1.0)

        # Resolve inputs
        albedo = expect_resource(
            exec_ctx.resources, self.g_albedo, TextureResource
        ).handle
        normal = expect_resource(
            exec_ctx.resources, self.g_normal, TextureResource
        ).handle
        orm = expect_resource(exec_ctx.resources, self.g_orm, TextureResource).handle
        depth = expect_resource(
            exec_ctx.resources, self.g_depth, TextureResource
        ).handle

        albedo.use(location=0)
        normal.use(location=1)
        orm.use(location=2)
        depth.use(location=3)

        # Program + uniforms
        assert self._vao is not None
        assert isinstance(self._program, moderngl.Program)
        assert self._u_light_count is not None
        assert self._u_light_pos_radius is not None
        assert self._u_light_color_intensity is not None

        lights = exec_ctx.frame.point_lights
        n = min(len(lights), self._max_lights)
        self._u_light_count.value = n

        pos_radius: list[tuple[float, float, float, float]] = []
        col_int: list[tuple[float, float, float, float]] = []
        for i in range(n):
            lp = lights[i]
            pos_radius.append(
                (
                    float(lp.position_ws[0]),
                    float(lp.position_ws[1]),
                    float(lp.position_ws[2]),
                    float(lp.radius),
                )
            )
            col_int.append(
                (
                    float(lp.color_rgb[0]),
                    float(lp.color_rgb[1]),
                    float(lp.color_rgb[2]),
                    float(lp.intensity),
                )
            )

        self._u_light_pos_radius.write(
            _pack_vec4_array(pos_radius, max_len=self._max_lights)
        )
        self._u_light_color_intensity.write(
            _pack_vec4_array(col_int, max_len=self._max_lights)
        )

        self._vao.render(mode=moderngl.TRIANGLES)

    def on_graph_destroyed(self) -> None:
        if self._vao is not None:
            self._vao.release()
        if self._fs_vbo is not None:
            self._fs_vbo.release()

        self._program = None
        self._vao = None
        self._fs_vbo = None
        self._u_light_count = None
        self._u_light_pos_radius = None
        self._u_light_color_intensity = None
