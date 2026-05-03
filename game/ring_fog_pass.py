from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import moderngl
import numpy as np

from sparrow.assets import AssetHandle, AssetServer
from sparrow.graphics.graph import (
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
    RenderServices,
)
from sparrow.graphics.resources import ShaderManager
from sparrow.graphics.utils import create_fullscreen_triangle, pack_mat4
from sparrow.graphics.utils.ids import ResourceId
from sparrow.graphics.utils.uniforms import set_uniform
from sparrow.types import Color3, Vector3

RING_FOG_VS_PATH = "../../game/shaders/ring_fog.vert"
RING_FOG_FS_PATH = "../../game/shaders/ring_fog.frag"


@dataclass
class RingFogPass(RenderPass):
    input_color: ResourceId
    input_depth: ResourceId
    target: Optional[ResourceId]

    ring_center: Vector3 = Vector3(0.0, 0.0, 0.0)
    ring_inner_radius: float = 11.13
    ring_outer_radius: float = 30.72
    ring_half_height: float = 0.1

    fog_color: Color3 = (0.42, 0.30, 0.18)
    base_density: float = 0.3

    _vs_handle: AssetHandle | None = None
    _fs_handle: AssetHandle | None = None
    _asset_server: AssetServer | None = None
    _shader_manager: ShaderManager | None = None
    _triangle_buffer: moderngl.Buffer | None = None
    _vao: moderngl.VertexArray | None = None

    def build(self) -> PassBuildInfo:
        reads = [
            PassResourceUse(self.input_color, "read"),
            PassResourceUse(self.input_depth, "read"),
        ]
        writes = [PassResourceUse(self.target, "write")] if self.target else []
        return PassBuildInfo(pass_id=self.pass_id, reads=reads, writes=writes)

    def on_compile(
        self, ctx: moderngl.Context, services: RenderServices
    ) -> None:
        self._shader_manager = services.shader_manager
        self._asset_server = services.gpu_resources.asset_server
        self._vs_handle = self._asset_server.load(RING_FOG_VS_PATH)
        self._fs_handle = self._asset_server.load(RING_FOG_FS_PATH)
        self._triangle_buffer = create_fullscreen_triangle(ctx)

    def on_destroy(self) -> None:
        if self._vao:
            self._vao.release()
            self._vao = None
        if self._triangle_buffer:
            self._triangle_buffer.release()
            self._triangle_buffer = None

    def execute(self, ctx: PassExecutionContext) -> None:
        assert (
            self._shader_manager
            and self._asset_server
            and self._vs_handle
            and self._fs_handle
            and self._triangle_buffer
        )

        program = self._shader_manager.get_program_from_assets(
            self._asset_server, self._vs_handle, self._fs_handle
        )
        if not program:
            return

        if not self._vao:
            self._vao = ctx.gl.vertex_array(
                program, [(self._triangle_buffer, "2f", "in_pos")]
            )

        if self.target:
            ctx.graph_resources[self.target].use()
        else:
            ctx.gl.screen.use()

        ctx.gl.disable(moderngl.DEPTH_TEST)

        color_tex = ctx.graph_resources[self.input_color]
        depth_tex = ctx.graph_resources[self.input_depth]
        color_tex.use(location=0)
        depth_tex.use(location=1)

        inv_view_proj = np.linalg.inv(ctx.frame.camera.view_proj).astype("f4")
        cam_pos = ctx.frame.camera.position

        set_uniform(program, "u_color_tex", 0)
        set_uniform(program, "u_depth_tex", 1)
        set_uniform(program, "u_inv_view_proj", pack_mat4(inv_view_proj.T))
        set_uniform(
            program,
            "u_camera_pos",
            (float(cam_pos[0]), float(cam_pos[1]), float(cam_pos[2])),
        )
        set_uniform(
            program,
            "u_ring_center",
            (
                self.ring_center.x,
                self.ring_center.y,
                self.ring_center.z,
            ),
        )
        set_uniform(program, "u_ring_inner_radius", self.ring_inner_radius)
        set_uniform(program, "u_ring_outer_radius", self.ring_outer_radius)
        set_uniform(program, "u_ring_half_height", self.ring_half_height)
        set_uniform(program, "u_fog_color", self.fog_color)
        set_uniform(program, "u_base_density", self.base_density)
        set_uniform(program, "u_time", float(ctx.frame.time))

        self._vao.render(mode=moderngl.TRIANGLES)
