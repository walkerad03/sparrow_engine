# sparrow/graphics/passes/forward.py
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

import moderngl

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
    expect_resource,
)
from sparrow.graphics.shaders.program_types import ShaderStages
from sparrow.graphics.shaders.shader_manager import ShaderRequest
from sparrow.graphics.util.ids import MaterialId, MeshId, PassId, ResourceId, ShaderId


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
class ForwardPass(RenderPass):
    pass_id: PassId
    out_albedo: Optional[ResourceId] = None
    out_depth: Optional[ResourceId] = None

    _program: moderngl.Program | None = None
    _u_view_proj: moderngl.Uniform | None = None
    _u_cam_pos: moderngl.Uniform | None = None

    _u_light_count: moderngl.Uniform | None = None
    _u_light_pos_radius: moderngl.Uniform | None = None
    _u_light_color_intensity: moderngl.Uniform | None = None

    _u_model: moderngl.Uniform | None = None
    _u_base_color: moderngl.Uniform | None = None
    _u_roughness: moderngl.Uniform | None = None
    _u_metalness: moderngl.Uniform | None = None

    _max_lights: int = 64

    @property
    def output_target(self) -> Optional[ResourceId]:
        return self.out_albedo

    def build(self) -> PassBuildInfo:
        writes = []
        if self.out_albedo:
            writes.append(PassResourceUse(self.out_albedo, "write", "color"))
        if self.out_depth:
            writes.append(PassResourceUse(self.out_depth, "write", "depth"))

        return PassBuildInfo(
            pass_id=self.pass_id,
            name="Forward",
            reads=[],
            writes=writes,
        )

    def on_graph_compiled(
        self,
        *,
        ctx: moderngl.Context,
        resources: Mapping[ResourceId, GraphResource[object]],
        services: RenderServices,
    ) -> None:
        req = ShaderRequest(
            shader_id=ShaderId("forward_pbr"),
            stages=ShaderStages(
                vertex="sparrow/graphics/shaders/default/forward_pbr.vert",
                fragment="sparrow/graphics/shaders/default/forward_pbr.frag",
            ),
            label="ForwardPBR",
        )
        prog_handle = services.shader_manager.get(req)

        if isinstance(prog_handle.program, moderngl.ComputeShader):
            raise RuntimeError(
                "ForwardPass requires a graphics Program, not a ComputeShader"
            )

        self._program = prog_handle.program

        self._u_view_proj = self._program["u_view_proj"]
        self._u_cam_pos = self._program["u_cam_pos"]

        self._u_light_count = self._program["u_light_count"]
        self._u_light_pos_radius = self._program["u_light_pos_radius"]
        self._u_light_color_intensity = self._program["u_light_color_intensity"]

        self._u_model = self._program["u_model"]
        self._u_base_color = self._program["u_base_color"]
        self._u_roughness = self._program["u_roughness"]
        self._u_metalness = self._program["u_metalness"]

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        gl = exec_ctx.gl
        resources = exec_ctx.resources
        services = exec_ctx.services
        frame = exec_ctx.frame

        if self.output_target:
            fbo = expect_resource(resources, self.output_fbo_id, FramebufferResource)
            fbo.handle.use()
        else:
            gl.screen.use()

        gl.viewport = (0, 0, exec_ctx.viewport_width, exec_ctx.viewport_height)
        gl.enable(moderngl.DEPTH_TEST)
        gl.clear()

        assert (
            self._program
            and self._u_view_proj
            and self._u_model
            and self._u_cam_pos
            and self._u_light_count
            and self._u_light_pos_radius
            and self._u_light_color_intensity
            and self._u_base_color
            and self._u_roughness
            and self._u_metalness
        )

        self._u_view_proj.write(frame.camera.view_proj.T.tobytes())
        self._u_cam_pos.value = tuple(frame.camera.position_ws)

        light_count = min(len(frame.point_lights), self._max_lights)
        self._u_light_count.value = light_count

        pos_radius = []
        col_intensity = []
        for i in range(light_count):
            lp = frame.point_lights[i]
            pos_radius.append((*lp.position_ws, lp.radius))
            col_intensity.append((*lp.color_rgb, lp.intensity))

        self._u_light_pos_radius.write(
            _pack_vec4_array(pos_radius, max_len=self._max_lights)
        )

        self._u_light_color_intensity.write(
            _pack_vec4_array(col_intensity, max_len=self._max_lights)
        )

        for draw in frame.draws:
            self._u_model.write(draw.model.T.tobytes())

            mat_id = MaterialId(draw.material_id)
            mesh_id = MeshId(draw.mesh_id)

            material = services.material_manager.get(mat_id)
            self._u_base_color.value = material.base_color_factor
            self._u_roughness.value = material.roughness
            self._u_metalness.value = material.metalness

            vao = services.mesh_manager.vao_for(mesh_id, self._program)
            vao.render(moderngl.TRIANGLES)

    def on_graph_destroyed(self) -> None:
        self._program = None
        self._u_view_proj = None
        self._u_model = None
