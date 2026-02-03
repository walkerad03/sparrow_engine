# sparrow/graphics/passes/forward.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import moderngl

from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
    RenderServices,
)
from sparrow.graphics.utils.ids import ResourceId
from sparrow.graphics.utils.uniforms import set_uniform


@dataclass
class ForwardPBRPass(RenderPass):
    """
    Standard Forward Rendering Pass.
    Draws all opaque objects in the RenderFrame.
    """

    target: Optional[ResourceId] = None

    _program: moderngl.Program | None = None

    def build(self) -> PassBuildInfo:
        writes = []
        if self.target:
            writes.append(PassResourceUse(self.target, "write"))

        return PassBuildInfo(
            pass_id=self.pass_id,
            reads=[],
            writes=writes,
        )

    def on_compile(
        self, ctx: moderngl.Context, services: RenderServices
    ) -> None:
        vs = """
        #version 330 core
        uniform mat4 u_view_proj;
        uniform mat4 u_model;

        layout (location = 0) in vec3 in_pos;
        layout (location = 1) in vec3 in_normal;
        layout (location = 2) in vec2 in_uv;

        out vec3 v_normal;
        out vec2 v_uv;

        void main() {
            v_normal = in_normal;
            v_uv = in_uv;
            gl_Position = u_view_proj * u_model * vec4(in_pos, 1.0);
        }
        """

        fs = """
        #version 330 core
        uniform vec3 u_color;

        in vec3 v_normal;
        in vec2 v_uv;
        out vec4 fragColor;

        void main() {
            // Simple Debug Lighting (N dot L)
            vec3 L = normalize(vec3(0.5, 1.0, 0.5));
            float NdotL = max(dot(normalize(v_normal), L), 0.1);
            vec3 uv_tint = vec3(v_uv, 0.0) * 0.0001;
            fragColor = vec4(u_color * NdotL + uv_tint, 1.0);
        }
        """
        self._program = services.shader_manager.get_program(vs, fs)

    def execute(self, ctx: PassExecutionContext) -> None:
        if not self._program:
            return

        gl = ctx.gl
        frame = ctx.frame

        if self.target:
            ctx.graph_resources[self.target].use()
        else:
            gl.screen.use()

        gl.enable(moderngl.DEPTH_TEST)
        gl.enable(moderngl.CULL_FACE)

        # TODO: Use UBOs
        set_uniform(
            self._program,
            "u_view_proj",
            frame.camera.view_proj.T.tobytes(),
        )

        for obj in frame.objects:
            gpu_mesh = ctx.gpu_resources.get_mesh(obj.mesh_id)
            if not gpu_mesh:
                continue

            set_uniform(
                self._program,
                "u_model",
                obj.transform.T.astype("f4").tobytes(),
            )

            set_uniform(
                self._program,
                "u_color",
                obj.color[:3],
            )

            if not gpu_mesh._default_vao:
                gpu_mesh.create_default_vao(
                    self._program, "3f 3f 2f", ["in_pos", "in_normal", "in_uv"]
                )

            gpu_mesh.render()
