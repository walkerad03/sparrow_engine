# sparrow/graphics/passes/gbuffer.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

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


@dataclass(slots=True)
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
    g_albedo: ResourceId
    g_normal: ResourceId
    g_orm: ResourceId
    g_depth: ResourceId

    _program: moderngl.Program | None = None
    _u_model: moderngl.Uniform | None = None
    _u_view_proj: moderngl.Uniform | None = None

    _u_base_color: moderngl.Uniform | None = None
    _u_roughness: moderngl.Uniform | None = None
    _u_metalness: moderngl.Uniform | None = None

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
        shader_mgr = services.shader_manager

        req = ShaderRequest(
            shader_id=ShaderId("gbuffer"),
            stages=ShaderStages(
                vertex="sparrow/graphics/shaders/default/gbuffer.vert",
                fragment="sparrow/graphics/shaders/default/gbuffer.frag",
            ),
            label="GBuffer",
        )

        prog = shader_mgr.get(req).program

        assert isinstance(prog, moderngl.Program)
        assert isinstance(prog["u_model"], moderngl.Uniform)
        assert isinstance(prog["u_view_proj"], moderngl.Uniform)

        self._program = prog
        self._u_model = prog["u_model"]
        self._u_view_proj = prog["u_view_proj"]

        self._u_base_color: moderngl.Uniform = self._program["u_base_color"]
        self._u_roughness: moderngl.Uniform = self._program["u_roughness"]
        self._u_metalness: moderngl.Uniform = self._program["u_metalness"]

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        """Render draw list into the GBuffer framebuffer."""
        gl = exec_ctx.gl

        fbo_res = expect_resource(
            exec_ctx.resources,
            ResourceId(f"fbo:{self.pass_id}"),
            FramebufferResource,
        )
        fbo = fbo_res.handle

        fbo.use()
        gl.enable(moderngl.DEPTH_TEST)
        gl.clear()

        services = exec_ctx.services

        assert isinstance(self._program, moderngl.Program)
        assert self._u_model and self._u_view_proj
        assert self._u_base_color and self._u_roughness and self._u_metalness

        self._u_view_proj.write(exec_ctx.frame.camera.view_proj.T.tobytes())

        for draw in exec_ctx.frame.draws:
            mesh_id = MeshId(draw.mesh_id)
            material_id = MaterialId(draw.material_id)

            material = services.material_manager.get(material_id)

            self._u_model.write(draw.model.T.tobytes())

            self._u_base_color.value = material.base_color_factor
            self._u_roughness.value = material.roughness
            self._u_metalness.value = material.metalness

            vao = services.mesh_manager.vao_for(mesh_id, self._program)
            vao.render()

    def on_graph_destroyed(self) -> None:
        """Release any cached state owned by the pass (if applicable)."""
        self._program = None
