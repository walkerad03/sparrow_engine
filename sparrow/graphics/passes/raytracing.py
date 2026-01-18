# sparrow/graphics/passes/raytrace.py
import struct
from collections.abc import Mapping
from dataclasses import dataclass

import moderngl
import numpy as np

from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassExecutionContext,
    PassFeatures,
    PassResourceUse,
    RenderPass,
    RenderServices,
)
from sparrow.graphics.graph.resources import (
    GraphResource,
    TextureResource,
    expect_resource,
)
from sparrow.graphics.renderer.settings import RaytracingRendererSettings
from sparrow.graphics.shaders.program_types import ShaderStages
from sparrow.graphics.shaders.shader_manager import ShaderRequest
from sparrow.graphics.util.ids import MaterialId, MeshId, PassId, ResourceId, ShaderId


@dataclass(kw_only=True)
class RaytracingPass(RenderPass):
    pass_id: PassId
    out_texture: ResourceId
    settings: RaytracingRendererSettings

    features: PassFeatures = PassFeatures.CAMERA | PassFeatures.SUN | PassFeatures.TIME

    _triangle_buffer: moderngl.Buffer | None = None
    _light_buffer: moderngl.Buffer | None = None

    def build(self) -> PassBuildInfo:
        return PassBuildInfo(
            pass_id=self.pass_id,
            name="Raytrace",
            reads=[],
            writes=[PassResourceUse(self.out_texture, "write", "storage", binding=0)],
        )

    def on_graph_compiled(
        self,
        *,
        ctx: moderngl.Context,
        resources: Mapping[ResourceId, GraphResource[object]],
        services: RenderServices,
    ) -> None:
        req = ShaderRequest(
            shader_id=ShaderId("raytrace_comp"),
            stages=ShaderStages(
                compute="sparrow/graphics/shaders/default/raytrace.comp"
            ),
            label="Raytrace",
        )
        self._program = services.shader_manager.get(req).program

        super().on_graph_compiled(ctx=ctx, resources=resources, services=services)

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        self.execute_base(exec_ctx)
        assert isinstance(self._program, moderngl.ComputeShader)

        resources = exec_ctx.resources

        out_res = expect_resource(resources, self.out_texture, TextureResource)
        out_res.handle.bind_to_image(0, read=True, write=True)

        self._update_buffers(exec_ctx)

        w, h = exec_ctx.viewport_width, exec_ctx.viewport_height
        gw, gh = 16, 16
        nx = (w + gw - 1) // gw
        ny = (h + gh - 1) // gh

        self._program.run(nx, ny, 1)

    def _update_buffers(self, exec_ctx: PassExecutionContext) -> None:
        triangle_data = []
        services = exec_ctx.services
        assert self._program

        if "u_max_bounces" in self._program:
            self._program["u_max_bounces"].value = self.settings.max_bounces

        if "u_samples_per_pixel" in self._program:
            self._program["u_samples_per_pixel"].value = self.settings.samples_per_pixel

        if "u_denoiser_enabled" in self._program:
            self._program["u_denoiser_enabled"].value = self.settings.denoiser_enabled

        for draw in exec_ctx.frame.draws:
            mesh_id = MeshId(draw.mesh_id)
            mesh_handle = services.mesh_manager.get(mesh_id)
            mesh_data = mesh_handle.data

            material_id = MaterialId(draw.material_id)
            material = services.material_manager.get(material_id)

            # 1. Parse vertices (assuming 8 floats: pos, normal, uv)
            raw_verts = np.frombuffer(mesh_data.vertices, dtype=np.float32)
            positions = raw_verts.reshape(-1, 8)[:, :3]

            # 2. Check for indices
            if mesh_data.indices is not None:
                # Assuming 32-bit unsigned integers for indices
                indices = np.frombuffer(mesh_data.indices, dtype=np.uint32)

                # Iterate through indices in steps of 3
                for i in range(0, len(indices), 3):
                    idx0, idx1, idx2 = indices[i], indices[i + 1], indices[i + 2]

                    v0_local = np.append(positions[idx0], 1.0)
                    v1_local = np.append(positions[idx1], 1.0)
                    v2_local = np.append(positions[idx2], 1.0)

                    # Transform and pack as before
                    v0_world = (draw.model @ v0_local)[:3]
                    v1_world = (draw.model @ v1_local)[:3]
                    v2_world = (draw.model @ v2_local)[:3]
                    triangle_data.extend(
                        [*v0_world, 0.0, *v1_world, 0.0, *v2_world, 0.0]
                    )
            else:
                # Fallback for non-indexed geometry
                for i in range(0, len(positions), 3):
                    v0_local = np.append(positions[i], 1.0)
                    v1_local = np.append(positions[i + 1], 1.0)
                    v2_local = np.append(positions[i + 2], 1.0)

                    mat_color_vec4 = getattr(
                        material, "base_color_factor", (1.0, 1.0, 1.0, 1.0)
                    )
                    albedo_rgb = mat_color_vec4[:3]
                    metalness = getattr(material, "metalness", 0.0)
                    roughness = getattr(material, "roughness", 0.5)

                    v0_world = (draw.model @ v0_local)[:3]
                    v1_world = (draw.model @ v1_local)[:3]
                    v2_world = (draw.model @ v2_local)[:3]
                    triangle_data.extend(
                        [
                            *v0_world,
                            metalness,
                            *v1_world,
                            roughness,
                            *v2_world,
                            0.0,
                            *albedo_rgb,
                            0.0,
                        ]
                    )

        if triangle_data:
            raw_data = struct.pack(f"{len(triangle_data)}f", *triangle_data)
            if self._triangle_buffer is None or self._triangle_buffer.size < len(
                raw_data
            ):
                if self._triangle_buffer:
                    self._triangle_buffer.release()
                self._triangle_buffer = exec_ctx.gl.buffer(raw_data)
            else:
                self._triangle_buffer.write(raw_data)

            self._triangle_buffer.bind_to_storage_buffer(binding=1)
            self._program["u_triangle_count"].value = len(triangle_data) // 16

        # Lights
        light_data = []
        for light in exec_ctx.frame.point_lights:
            light_data.extend(
                [*light.position_ws, 0.0, *light.color_rgb, light.intensity]
            )

        if light_data:
            raw_lights = struct.pack(f"{len(light_data)}f", *light_data)
            if self._light_buffer is None or self._light_buffer.size < len(raw_lights):
                if self._light_buffer:
                    self._light_buffer.release()
                self._light_buffer = exec_ctx.gl.buffer(raw_lights)
            else:
                self._light_buffer.write(raw_lights)

            self._light_buffer.bind_to_storage_buffer(binding=2)
            self._program["u_light_count"].value = len(exec_ctx.frame.point_lights)
