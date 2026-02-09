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

        content = [(self.vbo, "3f 3f 2f", "in_pos", "in_normal", "in_uv")]
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

        # TODO: In the future, pass these attribute names in dynamically if needed
        content = [
            (self.vbo, "3f 3f 2f", "in_pos", "in_normal", "in_uv"),
        ]

        content.append((instance_buffer, "16f 4f /i", "i_model", "i_color"))

        vao = self._ctx.vertex_array(program, content, index_buffer=self.ibo)
        self._vaos[key] = vao
        return vao

    def release(self) -> None:
        self.vbo.release()
        if self.ibo:
            self.ibo.release()

        for vao in self._vaos.values():
            vao.release()
        self._vaos.clear()
