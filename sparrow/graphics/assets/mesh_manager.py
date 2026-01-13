# sparrow/graphics/assets/mesh_manager.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import moderngl

from sparrow.graphics.assets.types import MeshData
from sparrow.graphics.shaders.program_types import ProgramHandle
from sparrow.graphics.util.ids import MeshId


@dataclass(slots=True)
class MeshHandle:
    """GPU-side mesh representation."""

    vbo: moderngl.Buffer
    ibo: Optional[moderngl.Buffer]
    vao_cache: Dict[int, moderngl.VertexArray]  # keyed by program id/hash
    label: str


class MeshManager:
    """Creates and caches GPU meshes; builds VAOs per program as needed."""

    def __init__(self, gl: moderngl.Context) -> None: ...

    def create(self, mesh_id: MeshId, data: MeshData, *, label: str = "") -> MeshHandle:
        """Upload a mesh and store it under mesh_id."""
        raise NotImplementedError

    def get(self, mesh_id: MeshId) -> MeshHandle:
        """Retrieve an existing mesh handle."""
        raise NotImplementedError

    def vao_for(self, mesh_id: MeshId, program: ProgramHandle) -> moderngl.VertexArray:
        """Create or reuse a VAO for the given mesh and program."""
        raise NotImplementedError
