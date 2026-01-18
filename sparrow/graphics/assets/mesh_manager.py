# sparrow/graphics/assets/mesh_manager.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import moderngl

from sparrow.graphics.assets.obj_loader import load_obj
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
    data: MeshData


class MeshManager:
    """Creates and caches GPU meshes; builds VAOs per program as needed."""

    def __init__(self, gl: moderngl.Context) -> None:
        self._gl = gl
        self._meshes: Dict[MeshId, MeshHandle] = {}

        self._load_engine_defaults()

    def _load_engine_defaults(self) -> None:
        self.create(
            MeshId("engine.suzanne"),
            load_obj("sparrow/graphics/meshes/default/suzanne.obj"),
            label="Suzanne",
        )

        self.create(
            MeshId("engine.cube"),
            load_obj("sparrow/graphics/meshes/default/cube.obj"),
            label="Cube",
        )

        """
        self.create(
            MeshId("engine.dense_icosphere"),
            load_obj("sparrow/graphics/meshes/default/dense_icosphere.obj"),
            label="Dense Icosphere",
        )
        """
        self.create(
            MeshId("engine.stanford_dragon"),
            load_obj("sparrow/graphics/meshes/default/xyzrgb_dragon.obj"),
            label="Stanford Dragon",
        )

        self.create(
            MeshId("engine.stanford_bunny"),
            load_obj("sparrow/graphics/meshes/default/stanford-bunny.obj"),
            label="Stanford Bunny",
        )

        self.create(
            MeshId("engine.large_plane"),
            load_obj("sparrow/graphics/meshes/default/large_plane.obj"),
            label="Large Plane",
        )

        self.create(
            MeshId("engine.stanford_dragon_lowpoly"),
            load_obj("sparrow/graphics/meshes/default/xyzrgb_dragon_decimated.obj"),
            label="Stanford Dragon (Low Poly)",
        )

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
            data=data,
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

        program_attribs: dict[str, moderngl.Attribute] = {}
        for name in program:
            member = program[name]
            if isinstance(member, moderngl.Attribute):
                program_attribs[name] = member

        if not program_attribs:
            raise RuntimeError("Program has no vertex attributes")

        layout = mesh.vertex_layout
        format_parts = layout.format.split()

        final_fmt_parts = []
        final_attrs = []

        for attr_name, fmt in zip(layout.attributes, format_parts):
            if attr_name in program_attribs:
                final_fmt_parts.append(fmt)
                final_attrs.append(attr_name)
            else:
                size_bytes = _format_size(fmt)
                final_fmt_parts.append(f"{size_bytes}x")

        final_format_str = " ".join(final_fmt_parts)
        content = [(mesh.vbo, final_format_str, *final_attrs)]

        if not final_attrs:
            raise RuntimeError(
                f"No compatible vertex attributes between mesh '{mesh_id}' "
                f"and program {id(program)}"
            )

        vao = self._gl.vertex_array(program, content)
        mesh.vao_cache[key] = vao
        return vao


def _format_size(fmt: str) -> int:
    # fmt examples: "3f", "2f", "4i"
    count = int(fmt[:-1])
    kind = fmt[-1]

    if kind == "f":
        return count * 4
    if kind == "i":
        return count * 4
    if kind == "h":
        return count * 2

    raise ValueError(f"Unsupported vertex format: {fmt}")
