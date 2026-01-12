from __future__ import annotations

import array
from dataclasses import dataclass
from typing import Dict

import moderngl


@dataclass(frozen=True)
class Mesh:
    vbo: moderngl.Buffer
    layout: tuple[str, ...]
    attribs: tuple[str, ...]
    mode: int
    vertex_count: int | None = None


class MeshLibrary:
    def __init__(self, ctx: moderngl.Context):
        self._ctx = ctx
        self._meshes: Dict[str, Mesh] = {}

        self._register_quad()
        self._register_cube()

    def register(self, key: str, mesh: Mesh) -> None:
        self._meshes[key] = mesh

    def get(self, key: str) -> Mesh:
        return self._meshes[key]

    def _register_quad(self) -> None:
        vertices = array.array(
            "f",
            [
                # x, y, z, u, v
                -0.5,
                -0.5,
                0.0,
                0.0,
                0.0,
                0.5,
                -0.5,
                0.0,
                1.0,
                0.0,
                -0.5,
                0.5,
                0.0,
                0.0,
                1.0,
                0.5,
                0.5,
                0.0,
                1.0,
                1.0,
            ],
        )

        vbo = self._ctx.buffer(vertices.tobytes())

        self._meshes["quad"] = Mesh(
            vbo=vbo,
            layout=("3f 2f",),
            attribs=("in_pos", "in_uv"),
            mode=moderngl.TRIANGLE_STRIP,
            vertex_count=4,
        )

    def _register_cube(self) -> None:
        # 36 vertices (6 faces * 2 triangles * 3 vertices)
        # Format: x, y, z, u, v
        vertices = array.array(
            "f",
            [
                # Front Face
                -0.5,
                -0.5,
                0.5,
                0.0,
                0.0,
                0.5,
                -0.5,
                0.5,
                1.0,
                0.0,
                0.5,
                0.5,
                0.5,
                1.0,
                1.0,
                0.5,
                0.5,
                0.5,
                1.0,
                1.0,
                -0.5,
                0.5,
                0.5,
                0.0,
                1.0,
                -0.5,
                -0.5,
                0.5,
                0.0,
                0.0,
                # Back Face
                0.5,
                -0.5,
                -0.5,
                0.0,
                0.0,
                -0.5,
                -0.5,
                -0.5,
                1.0,
                0.0,
                -0.5,
                0.5,
                -0.5,
                1.0,
                1.0,
                -0.5,
                0.5,
                -0.5,
                1.0,
                1.0,
                0.5,
                0.5,
                -0.5,
                0.0,
                1.0,
                0.5,
                -0.5,
                -0.5,
                0.0,
                0.0,
                # Left Face
                -0.5,
                -0.5,
                -0.5,
                0.0,
                0.0,
                -0.5,
                -0.5,
                0.5,
                1.0,
                0.0,
                -0.5,
                0.5,
                0.5,
                1.0,
                1.0,
                -0.5,
                0.5,
                0.5,
                1.0,
                1.0,
                -0.5,
                0.5,
                -0.5,
                0.0,
                1.0,
                -0.5,
                -0.5,
                -0.5,
                0.0,
                0.0,
                # Right Face
                0.5,
                -0.5,
                0.5,
                0.0,
                0.0,
                0.5,
                -0.5,
                -0.5,
                1.0,
                0.0,
                0.5,
                0.5,
                -0.5,
                1.0,
                1.0,
                0.5,
                0.5,
                -0.5,
                1.0,
                1.0,
                0.5,
                0.5,
                0.5,
                0.0,
                1.0,
                0.5,
                -0.5,
                0.5,
                0.0,
                0.0,
                # Top Face
                -0.5,
                0.5,
                0.5,
                0.0,
                0.0,
                0.5,
                0.5,
                0.5,
                1.0,
                0.0,
                0.5,
                0.5,
                -0.5,
                1.0,
                1.0,
                0.5,
                0.5,
                -0.5,
                1.0,
                1.0,
                -0.5,
                0.5,
                -0.5,
                0.0,
                1.0,
                -0.5,
                0.5,
                0.5,
                0.0,
                0.0,
                # Bottom Face
                -0.5,
                -0.5,
                -0.5,
                0.0,
                0.0,
                0.5,
                -0.5,
                -0.5,
                1.0,
                0.0,
                0.5,
                -0.5,
                0.5,
                1.0,
                1.0,
                0.5,
                -0.5,
                0.5,
                1.0,
                1.0,
                -0.5,
                -0.5,
                0.5,
                0.0,
                1.0,
                -0.5,
                -0.5,
                -0.5,
                0.0,
                0.0,
            ],
        )

        vbo = self._ctx.buffer(vertices.tobytes())

        self._meshes["cube"] = Mesh(
            vbo=vbo,
            layout=("3f 2f",),
            attribs=("in_pos", "in_uv"),
            mode=moderngl.TRIANGLES,  # Use Triangles for full cube
            vertex_count=36,
        )
