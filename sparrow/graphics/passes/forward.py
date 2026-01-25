# sparrow/graphics/passes/forward.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

import moderngl
import numpy as np

from sparrow.graphics.ecs.frame_submit import LightPoint
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
    expect_resource,
)
from sparrow.graphics.renderer.settings import ForwardRendererSettings
from sparrow.graphics.shaders.program_types import ShaderStages
from sparrow.graphics.shaders.shader_manager import ShaderRequest
from sparrow.graphics.util.ids import (
    MaterialId,
    MeshId,
    PassId,
    ResourceId,
    ShaderId,
)


@dataclass(kw_only=True)
class ForwardPass(RenderPass):
    pass_id: PassId
    settings: ForwardRendererSettings

    albedo_tex: ResourceId
    depth_tex: ResourceId

    features: PassFeatures = PassFeatures.CAMERA

    _u_model: moderngl.Uniform | None = None
    _u_light_color: moderngl.Uniform | None = None
    _u_light_pos: moderngl.Uniform | None = None

    _u_mat_albedo: moderngl.Uniform | None = None
    _u_mat_roughness: moderngl.Uniform | None = None
    _u_mat_metallic: moderngl.Uniform | None = None

    @property
    def output_target(self) -> Optional[ResourceId]:
        return self.albedo_tex

    def build(self) -> PassBuildInfo:
        writes = [
            PassResourceUse(
                resource=self.depth_tex,
                access="write",
                stage="depth",
                binding=0,
            )
        ]

        if self.output_target:
            writes.append(
                PassResourceUse(
                    resource=self.output_target,
                    access="write",
                    stage="color",
                    binding=0,
                )
            )
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
                vertex="sparrow/graphics/shaders/default/forward.vert",
                fragment="sparrow/graphics/shaders/default/forward.frag",
            ),
            label="Forward",
        )
        prog = services.shader_manager.get(req).program
        if isinstance(prog, moderngl.ComputeShader):
            raise RuntimeError(
                "ForwardPass requires a graphics Program, not a ComputeShader"
            )

        self._u_model: moderngl.Uniform = prog.get("u_model", None)
        self._u_light_color: moderngl.Uniform = prog.get("u_light_color", None)
        self._u_light_pos: moderngl.Uniform = prog.get("u_light_pos", None)

        self._u_mat_albedo: moderngl.Uniform = prog.get(
            "u_material.albedo", None
        )
        self._u_mat_roughness: moderngl.Uniform = prog.get(
            "u_material.roughness", None
        )
        self._u_mat_metallic: moderngl.Uniform = prog.get(
            "u_material.metallic", None
        )

        self._program = prog
        super().on_graph_compiled(
            ctx=ctx, resources=resources, services=services
        )

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        self.execute_base(exec_ctx)

        gl = exec_ctx.gl
        services = exec_ctx.services

        if self.output_target:
            fbo_res = expect_resource(
                exec_ctx.resources, self.output_fbo_id, FramebufferResource
            )
            fbo = fbo_res.handle
            fbo.use()
        else:
            gl.screen.use()

        gl.viewport = (0, 0, exec_ctx.viewport_width, exec_ctx.viewport_height)

        gl.enable(moderngl.DEPTH_TEST)
        gl.clear()

        assert isinstance(self._program, moderngl.Program)
        assert self._u_model

        light_color = (0.0, 0.0, 0.0)
        light_pos = (0.0, 0.0, 0.0)
        if exec_ctx.frame.point_lights:
            li: LightPoint = exec_ctx.frame.point_lights[0]
            light_color = (
                li.color_rgb[0],
                li.color_rgb[1],
                li.color_rgb[2],
            )
            light_pos = (
                li.position_ws[0],
                li.position_ws[1],
                li.position_ws[2],
            )
            light_intensity: float = li.intensity

        if self._u_light_color:
            self._u_light_color.value = [
                c * light_intensity for c in light_color
            ]

        if self._u_light_pos:
            self._u_light_pos.value = light_pos

        for draw in exec_ctx.frame.draws:
            mesh_id = MeshId(draw.mesh_id)
            material_id = MaterialId(draw.material_id)
            material = services.material_manager.get(material_id)

            self._u_model.write(draw.model.astype(np.float32).T.tobytes())

            if self._u_mat_albedo is not None:
                color = getattr(material, "albedo", (1.0, 1.0, 1.0))
                self._u_mat_albedo.value = color
            if self._u_mat_roughness:
                self._u_mat_roughness.value = getattr(
                    material, "roughness", 0.5
                )

            if self._u_mat_metallic:
                self._u_mat_metallic.value = getattr(material, "metallic", 0.0)

            vao = services.mesh_manager.vao_for(mesh_id, self._program)
            vao.render()

    def on_graph_destroyed(self) -> None:
        self._program = None
        self._u_model = None
        self._u_light_color = None
        self._u_light_pos = None
        self._u_mat_albedo = None
        self._u_mat_roughness = None
        self._u_mat_metallic = None
