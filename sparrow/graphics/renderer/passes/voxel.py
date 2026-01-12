from __future__ import annotations

from typing import Any, Callable

import moderngl
import numpy as np

from sparrow.core.components import transform_to_matrix
from sparrow.graphics.renderer.graph import RenderContext


class VoxelPass:
    name = "voxel"

    def __init__(
        self,
        *,
        prog: moderngl.Program,
        set_uniform: Callable[[moderngl.Program, str, Any], None],
        get_texture: Callable[[str], Any],
        world_size: tuple[float, float, float] = (512.0, 512.0, 256.0),
    ) -> None:
        self.prog = prog
        self._set = set_uniform
        self.get_texture = get_texture
        self.world_size = np.array(world_size, dtype="f4")

        self._vao_cache = {}

    def _iter_items(self, rc: RenderContext):
        for item in rc.draw_list.opaque:
            yield item
        for item in rc.draw_list.transparent:
            yield item

    def execute(self, rc: RenderContext) -> None:
        ctx = rc.ctx

        # Compute camera-centered voxel AABB
        center = np.array(rc.camera.current_target, dtype="f4")
        half = self.world_size * 0.5
        vox_min = center - half
        vox_max = center + half

        # Bind 3D textures as images for imageStore
        # Clear them first (camera-centered volume, so it changes every frame)
        vx, vy, vz = rc.frame.vox_res
        voxel_count = vx * vy * vz

        self._vox_clear_albedo = b"\x00" * (voxel_count * 4)
        self._vox_clear_normal = b"\x00" * (voxel_count * 8)

        rc.frame.vox_albedo_occ.write(self._vox_clear_albedo)
        rc.frame.vox_normal.write(self._vox_clear_normal)

        rc.frame.vox_albedo_occ.bind_to_image(0, read=False, write=True)
        rc.frame.vox_normal.bind_to_image(1, read=False, write=True)

        # Global uniforms
        self._set(self.prog, "u_vox_min", tuple(vox_min.tolist()))
        self._set(self.prog, "u_vox_max", tuple(vox_max.tolist()))
        self._set(self.prog, "u_vox_res", rc.frame.vox_res)

        # State
        ctx.disable(moderngl.DEPTH_TEST | moderngl.BLEND)

        # Voxelize geometry
        for item in self._iter_items(rc):
            renderable = item.renderable
            mesh = rc.meshes.get(renderable.mesh_id)

            vao = self._vao_cache.get(mesh)
            if not vao:
                vao = ctx.vertex_array(
                    self.prog, [(mesh.vbo, mesh.layout[0], *mesh.attribs)]
                )
                self._vao_cache[mesh] = vao

            model = transform_to_matrix(item.position, item.rotation, item.scale)
            self._set(self.prog, "u_model", model.tobytes())

            tex = self.get_texture(renderable.material)
            tex.use(0)
            self._set(self.prog, "u_albedo", 0)

            # Use the mesh's intended primitive mode
            assert mesh.vertex_count is not None
            vao.render(mode=mesh.mode, vertices=mesh.vertex_count)

        # Build mipmaps so the cone tracer can use LOD
        rc.frame.vox_albedo_occ.build_mipmaps()
        rc.frame.vox_normal.build_mipmaps()

        # Optional: Unbind images if you want explicit hygiene
        # ModernGL does not require this step
