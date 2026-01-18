# sparrow/graphics/passes/gbuffer.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

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
    expect_resource,
)
from sparrow.graphics.renderer.settings import DeferredRendererSettings
from sparrow.graphics.shaders.program_types import ShaderStages
from sparrow.graphics.shaders.shader_manager import ShaderRequest
from sparrow.graphics.util.ids import MaterialId, MeshId, PassId, ResourceId, ShaderId


@dataclass(kw_only=True)
class GBufferPass(RenderPass):
    """
    Fills GBuffer attachments from opaque geometry.

    Typical outputs:
      - g_albedo (rgba8 or rgba16f)
      - g_normal (rgba16f)
      - g_orm    (rgba8/rgba16f)
      - g_depth  (depth24/depth32f)
    """

    pass_id: PassId
    settings: DeferredRendererSettings

    g_albedo: ResourceId
    g_normal: ResourceId
    g_orm: ResourceId
    g_depth: ResourceId

    features: PassFeatures = PassFeatures.CAMERA

    _u_model: moderngl.Uniform | None = None
    _u_base_color: moderngl.Uniform | None = None
    _u_roughness: moderngl.Uniform | None = None
    _u_metalness: moderngl.Uniform | None = None

    @property
    def output_target(self) -> ResourceId | None:
        return self.g_albedo

    def build(self) -> PassBuildInfo:
        """Declare GBuffer attachments as writes; may read material textures."""
        return PassBuildInfo(
            pass_id=self.pass_id,
            name="GBuffer",
            reads=[],
            writes=[
                PassResourceUse(self.g_albedo, "write", stage="color", binding=0),
                PassResourceUse(self.g_normal, "write", stage="color", binding=1),
                PassResourceUse(self.g_orm, "write", stage="color", binding=2),
                PassResourceUse(self.g_depth, "write", stage="depth"),
            ],
        )

    def on_graph_compiled(
        self,
        *,
        ctx: moderngl.Context,
        resources: Mapping[ResourceId, GraphResource[object]],
        services: RenderServices,
    ) -> None:
        """Compile GBuffer shader program and cache uniform/attrib locations."""
        req = ShaderRequest(
            shader_id=ShaderId("gbuffer"),
            stages=ShaderStages(
                vertex="sparrow/graphics/shaders/default/gbuffer.vert",
                fragment="sparrow/graphics/shaders/default/gbuffer.frag",
            ),
            label="GBuffer",
        )

        prog = services.shader_manager.get(req).program
        if not isinstance(prog, moderngl.Program):
            raise RuntimeError("GBufferPass requires a graphics Program")

        if "u_model" not in prog:
            raise RuntimeError("Missing uniform u_model")
        self._u_model: moderngl.Uniform = prog["u_model"]

        self._u_base_color: moderngl.Uniform = prog.get("u_base_color", None)
        self._u_roughness: moderngl.Uniform = prog.get("u_roughness", None)
        self._u_metalness: moderngl.Uniform = prog.get("u_metalness", None)

        self._program = prog
        super().on_graph_compiled(ctx=ctx, resources=resources, services=services)

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        """Render draw list into the GBuffer framebuffer."""
        self.execute_base(exec_ctx)

        gl = exec_ctx.gl

        fbo_res = expect_resource(
            exec_ctx.resources, self.output_fbo_id, FramebufferResource
        )
        fbo = fbo_res.handle
        fbo.use()

        gl.viewport = (0, 0, fbo.size[0], fbo.size[1])

        gl.enable(moderngl.DEPTH_TEST)
        gl.disable(moderngl.BLEND)
        gl.clear()

        assert isinstance(self._program, moderngl.Program)
        assert self._u_model is not None

        services = exec_ctx.services

        for draw in exec_ctx.frame.draws:
            mesh_id = MeshId(draw.mesh_id)
            material_id = MaterialId(draw.material_id)

            material = services.material_manager.get(material_id)

            self._u_model.write(draw.model.T.tobytes())

            if self._u_base_color is not None and hasattr(
                material, "base_color_factor"
            ):
                self._u_base_color.value = material.base_color_factor
            if self._u_roughness is not None and hasattr(material, "roughness"):
                self._u_roughness.value = material.roughness
            if self._u_metalness is not None and hasattr(material, "metalness"):
                self._u_metalness.value = material.metalness

            vao = services.mesh_manager.vao_for(mesh_id, self._program)
            vao.render()

    def on_graph_destroyed(self) -> None:
        """Release any cached state owned by the pass (if applicable)."""
        self._program = None
        self._u_model = None
        self._u_base_color = None
        self._u_roughness = None
        self._u_metalness = None
