# sparrow/graphics/passes/shadow.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import moderngl
import numpy as np

from sparrow.assets import AssetHandle, AssetServer, DefaultShaders
from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
    RenderServices,
)
from sparrow.graphics.resources import ShaderManager
from sparrow.graphics.utils import pack_mat4
from sparrow.graphics.utils.batcher import RenderBatcher
from sparrow.graphics.utils.ids import ResourceId
from sparrow.graphics.utils.uniforms import set_uniform
from sparrow.math import create_look_at, create_ortho_projection
from sparrow.types import Vector3


@dataclass
class ShadowPass(RenderPass):
    """
    Depth-only pass to generate a shadow map from the sun's perspective.
    """

    target: Optional[ResourceId] = None

    _batcher: RenderBatcher | None = None
    _vs_handle: AssetHandle | None = None
    _fs_handle: AssetHandle | None = None

    _asset_server: AssetServer | None = None
    _shader_manager: ShaderManager | None = None

    def build(self) -> PassBuildInfo:
        writes = [PassResourceUse(self.target, "write")] if self.target else []
        return PassBuildInfo(pass_id=self.pass_id, reads=[], writes=writes)

    def on_compile(
        self, ctx: moderngl.Context, services: RenderServices
    ) -> None:
        self._batcher = RenderBatcher(ctx)
        self._shader_manager = services.shader_manager
        self._asset_server = services.gpu_resources.asset_server

        assert self._asset_server
        self._vs_handle = self._asset_server.load(DefaultShaders.SHADOW_VS)
        self._fs_handle = self._asset_server.load(DefaultShaders.SHADOW_FS)

    def on_destroy(self) -> None:
        if self._batcher:
            self._batcher.release()
            self._batcher = None

    def execute(self, ctx: PassExecutionContext) -> None:
        assert (
            self._shader_manager
            and self._asset_server
            and self._vs_handle
            and self._fs_handle
            and self._batcher
        )

        program = self._shader_manager.get_program_from_assets(
            self._asset_server, self._vs_handle, self._fs_handle
        )

        if not program:
            return

        gl = ctx.gl

        if self.target:
            ctx.graph_resources[self.target].use()
        else:
            return  # Must have a target

        gl.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        gl.cull_face = "back"

        # Calculate Light Space Matrix
        # For an "extremely simple" shadow map, we use a fixed orthographic volume
        # centered around the camera or scene origin.
        sun_dir = np.array(ctx.frame.sun_direction, dtype="f4")
        if np.linalg.norm(sun_dir) < 1e-6:
            sun_dir = np.array([0, -1, 0], dtype="f4")

        # Position light "up" along the sun direction
        light_pos = -sun_dir * 50.0
        light_view = create_look_at(
            light_pos, Vector3(0, 0, 0), Vector3(0, 1, 0)
        )

        # Orthographic projection for directional light
        size = 100.0
        light_proj = create_ortho_projection(
            -size, size, -size, size, 0.1, 300.0
        )

        light_space_mat = light_proj @ light_view

        set_uniform(program, "u_light_space_mat", pack_mat4(light_space_mat.T))

        if ctx.frame.mesh_ids.size > 0:
            batches = self._batcher.group_columns(
                ctx.frame.mesh_ids, ctx.frame.albedo_ids
            )

            for (mesh_id, _), indices in batches.items():
                gpu_mesh = ctx.gpu_resources.get_mesh(mesh_id)
                if not gpu_mesh:
                    continue

                self._batcher.prepare_instance_data_columns(
                    indices,
                    ctx.frame.transforms,
                    ctx.frame.colors,
                    ctx.frame.roughness,
                    ctx.frame.metallic,
                    ctx.frame.emissive,
                )

                vao = gpu_mesh.get_instanced_vao(program, self._batcher.buffer)
                vao.render(instances=int(indices.size))
        else:
            batches = self._batcher.group_objects(ctx.frame.objects)

            for (mesh_id, _), instances in batches.items():
                gpu_mesh = ctx.gpu_resources.get_mesh(mesh_id)
                if not gpu_mesh:
                    continue

                self._batcher.prepare_instance_data(
                    instances, ctx.frame.transforms
                )

                vao = gpu_mesh.get_instanced_vao(program, self._batcher.buffer)
                vao.render(instances=len(instances))

        gl.cull_face = "back"  # Restore
