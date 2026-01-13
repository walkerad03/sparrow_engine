# sparrow/graphics/assets/mesh_manager.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import moderngl

from sparrow.graphics.assets.types import MeshData, VertexLayout
from sparrow.graphics.util.ids import MeshId


@dataclass(slots=True)
class MeshHandle:
    """GPU-side mesh representation."""

    vbo: moderngl.Buffer
    ibo: Optional[moderngl.Buffer]
    vertex_layout: VertexLayout
    vao_cache: Dict[int, moderngl.VertexArray]  # keyed by program id/hash
    label: str


class MeshManager:
    """Creates and caches GPU meshes; builds VAOs per program as needed."""

    def __init__(self, gl: moderngl.Context) -> None:
        self._gl = gl
        self._meshes: Dict[MeshId, MeshHandle] = {}

    def create(self, mesh_id: MeshId, data: MeshData, *, label: str = "") -> MeshHandle:
        """Upload a mesh and store it under mesh_id."""
        if mesh_id in self._meshes:
            raise KeyError(f"Mesh '{mesh_id}' already exists")

        vbo = self._gl.buffer(data.vertices)

        ibo: Optional[moderngl.Buffer] = None
        if data.indices is not None:
            ibo = self._gl.buffer(data.indices)

        handle = MeshHandle(
            vbo=vbo,
            ibo=ibo,
            vertex_layout=data.vertex_layout,
            vao_cache={},
            label=label or str(mesh_id),
        )

        self._meshes[mesh_id] = handle
        return handle

    def get(self, mesh_id: MeshId) -> MeshHandle:
        """Retrieve an existing mesh handle."""
        try:
            return self._meshes[mesh_id]
        except KeyError:
            raise KeyError(f"Mesh '{mesh_id}' not found")

    def vao_for(
        self, mesh_id: MeshId, program: moderngl.Program
    ) -> moderngl.VertexArray:
        """Create or reuse a VAO for the given mesh and program."""
        mesh = self.get(mesh_id)
        key = id(program)

        vao = mesh.vao_cache.get(key)
        if vao is not None:
            return vao

        layout = mesh.vertex_layout

        vao = self._gl.vertex_array(
            program,
            [(mesh.vbo, layout.format, *layout.attributes)],
            index_buffer=mesh.ibo,
        )

        mesh.vao_cache[key] = vao
        return vao
