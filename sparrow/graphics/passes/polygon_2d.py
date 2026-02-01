import struct
from collections import defaultdict
from typing import Optional

import moderngl
import numpy as np

from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
)
from sparrow.graphics.graph.resources import (
    FramebufferResource,
    expect_resource,
)
from sparrow.graphics.shaders.program_types import ShaderStages
from sparrow.graphics.shaders.shader_manager import ShaderRequest
from sparrow.graphics.util.ids import ResourceId, ShaderId


class Polygon2DPass(RenderPass):
    color_target: Optional[ResourceId] = None

    _program: moderngl.Program | None = None
    _u_view_proj: moderngl.Uniform | None = None
    _fbo_rid: ResourceId | None = None

    _vbo: moderngl.Buffer | None = None
    _vao: moderngl.VertexArray | None = None

    BATCH_SIZE = 100_000

    @property
    def output_target(self) -> ResourceId | None:
        return self.color_target

    def build(self) -> PassBuildInfo:
        writes: list[PassResourceUse] = []
        if self.color_target:
            writes.append(PassResourceUse(self.color_target, "write", "color"))

        return PassBuildInfo(
            pass_id=self.pass_id,
            name="Polygon 2D Pass",
            reads=[],
            writes=writes,
        )

    def on_graph_compiled(
        self, *, ctx: moderngl.Context, resources, services
    ) -> None:
        req = ShaderRequest(
            shader_id=ShaderId("polygon_2d"),
            stages=ShaderStages(
                vertex="sparrow/graphics/shaders/default/polygon_2d.vert",
                fragment="sparrow/graphics/shaders/default/polygon_2d.frag",
            ),
            label="Polygon2D",
        )
        self._program = services.shader_manager.get(req).program

        self._u_view_proj = self._program["u_view_proj"]

        if self.color_target:
            self._fbo_rid = ResourceId(f"fbo:{self.pass_id}")
            if self._fbo_rid not in resources:
                raise RuntimeError(
                    f"Polygon2DPass expected framebuffer '{self._fbo_rid}'."
                )
        else:
            self._fbo_rid = None

        self._vbo = ctx.buffer(reserve=self.BATCH_SIZE * 24, dynamic=True)
        self._vao = ctx.vertex_array(
            self._program,
            [(self._vbo, "2f 4f", "in_position", "in_color")],
        )

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        if not self._program:
            return

        gl = exec_ctx.gl
        frame = exec_ctx.frame

        if self.output_target is None:
            gl.screen.use()
        else:
            assert self._fbo_rid
            fbo_res = expect_resource(
                exec_ctx.resources, self._fbo_rid, FramebufferResource
            )
            fbo_res.handle.use()

        w, h = exec_ctx.viewport_width, exec_ctx.viewport_height
        gl.viewport = (0, 0, w, h)
        gl.disable(moderngl.DEPTH_TEST)
        gl.enable(moderngl.BLEND)
        gl.clear()

        proj = self._ortho_projection(
            0, exec_ctx.viewport_width, 0, exec_ctx.viewport_height, -1.0, 1.0
        )
        if self._u_view_proj:
            self._u_view_proj.write(proj.tobytes())

        batches = defaultdict(bytearray)
        vertex_counts = defaultdict(int)

        for poly in frame.polygons:
            if not poly.vertices:
                continue

            mat = poly.model.T
            local_verts = np.array(
                [[v.x, v.y, 0.0, 1.0] for v in poly.vertices], dtype="f4"
            )

            world_verts_4d = local_verts @ mat
            world_verts = world_verts_4d[:, :2]

            num_v = len(world_verts)
            if num_v < 2:
                continue

            r, g, b, a = poly.color
            c_bytes = struct.pack("4f", r, g, b, a)

            key = (poly.layer, poly.stroke_width)

            target_batch = batches[key]

            for i in range(num_v - 1):
                target_batch.extend(
                    struct.pack("2f", world_verts[i][0], world_verts[i][1])
                )
                target_batch.extend(c_bytes)

                target_batch.extend(
                    struct.pack(
                        "2f", world_verts[i + 1][0], world_verts[i + 1][1]
                    )
                )
                target_batch.extend(c_bytes)

                vertex_counts[key] += 2

            if poly.closed:
                # Close loop: Last -> First
                target_batch.extend(
                    struct.pack("2f", world_verts[-1][0], world_verts[-1][1])
                )
                target_batch.extend(c_bytes)
                target_batch.extend(
                    struct.pack("2f", world_verts[0][0], world_verts[0][1])
                )
                target_batch.extend(c_bytes)
                vertex_counts[key] += 2

        sorted_keys = sorted(batches.keys(), key=lambda k: (k[0], k[1]))

        for key in sorted_keys:
            layer, width = key
            count = vertex_counts[key]
            if count == 0:
                continue

            self._vbo.write(batches[key])

            gl.line_width = width
            self._vao.render(moderngl.LINES, vertices=count)

    def _ortho_projection(self, l, r, b, t, n, f):
        """Standard Ortho Matrix"""
        rml, tmb, fmn = r - l, t - b, f - n
        return np.array(
            [
                [2.0 / rml, 0.0, 0.0, 0.0],
                [0.0, 2.0 / tmb, 0.0, 0.0],
                [0.0, 0.0, -2.0 / fmn, 0.0],
                [-(r + l) / rml, -(t + b) / tmb, -(f + n) / fmn, 1.0],
            ],
            dtype="f4",
        )

    def on_graph_destroyed(self) -> None:
        self._program = None
        self._u_view_proj = None
        self._fbo_rid = None
        if self._vbo:
            self._vbo.release()
        if self._vao:
            self._vao.release()
