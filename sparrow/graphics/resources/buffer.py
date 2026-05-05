# sparrow/graphics/resources/buffer.py
from typing import Dict, Tuple

import moderngl

from sparrow.assets.types import MeshData


class GPUMesh:
    """
    Holds the GPU resources for a mesh: VBO, IBO (optional), and VAO.
    """

    def __init__(
        self,
        ctx: moderngl.Context,
        data: MeshData,
        program: moderngl.Program | None = None,
    ) -> None:
        self._ctx = ctx
        self.vertex_count = (
            len(data.vertices) // data.vertex_layout.stride_bytes
        )
        self.index_count = data.index_count
        self.aabb = data.aabb

        self.vbo = ctx.buffer(data.vertices)
        self.ibo = ctx.buffer(data.indices) if data.indices else None

        self._vaos: Dict[Tuple[int, int], moderngl.VertexArray] = {}

    def get_default_vao(
        self, program: moderngl.Program
    ) -> moderngl.VertexArray:
        """Retrieves or creates a simple non-instanced VAO for this program."""
        key = (program.glo, 0)  # 0 = no instance buffer

        if key in self._vaos:
            return self._vaos[key]

        content = self._build_content(
            program,
            (self.vbo, "3f 3f 2f", "in_pos", "in_normal", "in_uv"),
        )
        vao = self._ctx.vertex_array(program, content, index_buffer=self.ibo)

        self._vaos[key] = vao
        return vao

    def get_instanced_vao(
        self, program: moderngl.Program, instance_buffer: moderngl.Buffer
    ) -> moderngl.VertexArray:
        """
        Create or retrieve a VAO that combines this Mesh's VBO
        with the provided Instance Buffer.
        """
        key = (program.glo, instance_buffer.glo)

        if key in self._vaos:
            return self._vaos[key]

        content = self._build_content(
            program,
            (self.vbo, "3f 3f 2f", "in_pos", "in_normal", "in_uv"),
            (
                instance_buffer,
                "16f 4f 4f /i",
                "i_model",
                "i_base_color",
                "i_material_params",
            ),
        )

        vao = self._ctx.vertex_array(program, content, index_buffer=self.ibo)
        self._vaos[key] = vao
        return vao

    def _build_content(self, program: moderngl.Program, *buffers_info):
        """
        Filters attributes and creates the ModernGL 'content' list.
        Handles padding for missing attributes.
        """
        final_content = []

        for buf, layout, *attribs in buffers_info:
            parts = layout.split()
            instanced = False
            if parts[-1] == "/i":
                instanced = True
                parts = parts[:-1]

            actual_parts = []
            actual_attribs = []

            for i, part in enumerate(parts):
                name = attribs[i]
                if name in program:
                    actual_parts.append(part)
                    actual_attribs.append(name)
                else:
                    # Convert to padding. e.g. "3f" -> "12x"
                    count = int(part[:-1])
                    actual_parts.append(f"{count * 4}x")

            if actual_attribs:
                fmt = " ".join(actual_parts)
                if instanced:
                    fmt += " /i"
                final_content.append((buf, fmt, *actual_attribs))

        return final_content

    def release(self) -> None:
        self.vbo.release()
        if self.ibo:
            self.ibo.release()

        for vao in self._vaos.values():
            vao.release()
        self._vaos.clear()
