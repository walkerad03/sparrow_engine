# sparrow/graphics/passes/forward_unlit.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

import moderngl
import numpy as np

from sparrow.graphics.assets.material_manager import Material
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
from sparrow.graphics.util.ids import (
    MaterialId,
    MeshId,
    PassId,
    ResourceId,
    ShaderId,
)


@dataclass(slots=True)
class ForwardUnlitPass(RenderPass):
    """
    Minimal forward rendering pass (bring-up).

    Purpose:
        - Prove the mesh path works (VBO/VAO + program + draw)
        - Render a simple triangle (or first draw submission) into a color target
        - Optionally render directly to screen (for fastest iteration)

    Contract:
        - If `color_target` is None, renders to `ctx.screen` (default framebuffer).
        - If `color_target` is provided, renders into a graph-owned texture via a
          graph-owned framebuffer (resource id: fbo:<pass_id>).
        - Ignores materials for now; outputs a constant color or basic vertex color.

    Expected usage:
        - In early bring-up, pass `color_target=None` and just verify a triangle is visible.
        - Later, set `color_target` to a graph-managed texture (e.g., gbuffer albedo).
    """

    pass_id: PassId
    color_target: Optional[ResourceId] = None
    depth_target: Optional[ResourceId] = None

    _program: moderngl.Program | None = None
    _u_view_proj: moderngl.Uniform | None = None
    _u_model: moderngl.Uniform | None = None
    _u_albedo: moderngl.Uniform | None = None
    _fbo_rid: ResourceId | None = None

    @property
    def output_target(self) -> ResourceId | None:
        return self.color_target

    def build(self) -> PassBuildInfo:
        writes: list[PassResourceUse] = []

        if self.color_target:
            writes.append(PassResourceUse(self.color_target, "write", "color"))

        if self.depth_target:
            writes.append(PassResourceUse(self.depth_target, "write", "depth"))

        return PassBuildInfo(
            pass_id=self.pass_id,
            name="Forward (Bring-up)",
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
            shader_id=ShaderId("forward_basic"),
            stages=ShaderStages(
                vertex="sparrow/graphics/shaders/default/forward_basic.vert",
                fragment="sparrow/graphics/shaders/default/forward_basic.frag",
            ),
            label="ForwardBasic",
        )
        prog_handle = services.shader_manager.get(req)

        if isinstance(prog_handle.program, moderngl.ComputeShader):
            raise RuntimeError(
                "ForwardPass requires a graphics Program, not a ComputeShader"
            )

        self._program = prog_handle.program

        self._u_view_proj = self._program["u_view_proj"]
        self._u_model = self._program["u_model"]
        self._u_albedo = self._program["u_albedo"]

        if (
            self._u_view_proj is None
            or self._u_model is None
            or self._u_albedo is None
        ):
            missing = [
                name
                for name, u in (
                    ("u_view_proj", self._u_view_proj),
                    ("u_model", self._u_model),
                    ("u_albedo", self._u_albedo),
                )
                if u is None
            ]
            raise RuntimeError(
                f"ForwardPass missing required uniforms: {missing}"
            )

        if self.color_target:
            self._fbo_rid = ResourceId(f"fbo:{self.pass_id}")
            if self._fbo_rid not in resources:
                raise RuntimeError(
                    f"ForwardPass expected framebuffer resource '{self._fbo_rid}' for pass '{self.pass_id}'."
                )
        else:
            self._fbo_rid = None

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        if self._program is None:
            raise RuntimeError("ForwardPass not compiled (missing program)")

        gl = exec_ctx.gl
        services = exec_ctx.services
        frame = exec_ctx.frame

        if self.output_target is None:
            gl.screen.use()
            gl.viewport = (
                0,
                0,
                exec_ctx.viewport_width,
                exec_ctx.viewport_height,
            )
            gl.clear()
        else:
            assert self._fbo_rid
            fbo_res = expect_resource(
                exec_ctx.resources,
                self.output_fbo_id,
                FramebufferResource,
            )
            fbo = fbo_res.handle
            fbo.use()

            gl.viewport = (
                0,
                0,
                exec_ctx.viewport_width,
                exec_ctx.viewport_height,
            )
            fbo.clear()

        gl.enable(moderngl.DEPTH_TEST)
        gl.disable(moderngl.BLEND)

        assert self._u_view_proj is not None
        self._u_view_proj.write(
            frame.camera.view_proj.astype(np.float32).T.tobytes()
        )

        assert self._u_model is not None
        assert self._u_albedo is not None

        for di in frame.draws:
            mesh_id = MeshId(di.mesh_id)
            mat_id = MaterialId(di.material_id)

            mat: Material = services.material_manager.get(mat_id)

            self._u_model.write(di.model.astype(np.float32).T.tobytes())
            self._u_albedo.value = mat.albedo

            vao = services.mesh_manager.vao_for(mesh_id, self._program)
            vao.render(mode=moderngl.TRIANGLES)

    def on_graph_destroyed(self) -> None:
        self._program = None
        self._u_view_proj = None
        self._u_model = None
        self._u_albedo = None
        self._fbo_rid = None
