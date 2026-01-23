# sparrow/graphics/passes/forward.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

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
    GraphResource,
    TextureResource,
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

    out_tex: ResourceId

    features: PassFeatures = PassFeatures.CAMERA

    _u_model: moderngl.Uniform | None = None
    _u_base_color: moderngl.Uniform | None = None

    @property
    def output_target(self) -> Optional[ResourceId]:
        return self.out_tex

    def build(self) -> PassBuildInfo:
        writes = []

        if self.out_tex:
            writes.append(
                PassResourceUse(
                    resource=self.out_tex,
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
        if "u_model" not in prog:
            raise RuntimeError("Missing uniform u_model")
        self._u_model: moderngl.Uniform = prog["u_model"]

        self._u_base_color: moderngl.Uniform = prog.get("u_base_color", None)

        self._program = prog
        super().on_graph_compiled(
            ctx=ctx, resources=resources, services=services
        )

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        self.execute_base(exec_ctx)

        gl = exec_ctx.gl
        services = exec_ctx.services

        if self.out_tex:
            fbo_res = expect_resource(
                exec_ctx.resources, self.out_tex, TextureResource
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

        for draw in exec_ctx.frame.draws:
            mesh_id = MeshId(draw.mesh_id)
            material_id = MaterialId(draw.material_id)
            material = services.material_manager.get(material_id)

            self._u_model.write(draw.model.T.tobytes())

            if self._u_base_color is not None:
                color = getattr(
                    material, "base_color_factor", (1.0, 1.0, 1.0, 1.0)
                )
                self._u_base_color.value = color

            vao = services.mesh_manager.vao_for(mesh_id, self._program)
            vao.render()

    def on_graph_destroyed(self) -> None:
        self._program = None
        self._u_model = None
        self._u_base_color = None
