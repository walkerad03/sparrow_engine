# sparrow/graphics/resources/buffer.py
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

        self._default_vao = None
        if program:
            self.create_default_vao(
                program,
                data.vertex_layout.format,
                data.vertex_layout.attributes,
            )

    def create_default_vao(
        self, program: moderngl.Program, fmt: str, attrs: list[str]
    ) -> None:
        """Helper to create a VAO for a specific shader."""
        content = [(self.vbo, fmt, *attrs)]
        self._default_vao = self._ctx.vertex_array(
            program, content, index_buffer=self.ibo
        )

    def render(self, instances: int = 1) -> None:
        """Render using the default VAO (if created)."""
        if not self._default_vao:
            raise RuntimeError(
                "Cannot render GPUMesh without a bound Program/VAO."
            )
        self._default_vao.render(
            vertices=self.vertex_count, instances=instances
        )

    def release(self) -> None:
        self.vbo.release()
        if self.ibo:
            self.ibo.release()
        if self._default_vao:
            self._default_vao.release()
