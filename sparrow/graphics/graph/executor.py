# sparrow/graphics/graph/executor.py
from __future__ import annotations

from typing import Dict, List

import moderngl

from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.graph.pass_base import (
    PassExecutionContext,
    RenderPass,
    RenderServices,
)
from sparrow.graphics.integration.frame import RenderFrame
from sparrow.graphics.utils.ids import ResourceId


class GraphExecutor:
    """
    Manages the lifecycle and execution of a compiled Render Graph.
    """

    def __init__(
        self,
        ctx: moderngl.Context,
        builder: RenderGraphBuilder,
        services: RenderServices,
    ):
        self.ctx = ctx
        self.services = services
        self.passes: List[RenderPass] = list(builder.passes.values())

        # Transient Resources (Owned by Graph)
        self._textures: Dict[ResourceId, moderngl.Texture] = {}
        self._buffers: Dict[ResourceId, moderngl.Buffer] = {}
        self._framebuffers: Dict[ResourceId, moderngl.Framebuffer] = {}

        # Resource Definitions (for resizing)
        self._tex_defs = builder.textures
        self._buf_defs = builder.buffers
        self._fbo_defs = builder.framebuffers

        # 1. Compile Resources
        self._create_resources(1920, 1080)  # Default start size

        for p in self.passes:
            p.build()
            p.on_compile(ctx, services)

    def execute(self, frame: RenderFrame) -> None:
        """
        Run the graph for the given frame.
        """

        resources_map = {
            **self._textures,
            **self._buffers,
            **self._framebuffers,
        }

        exec_ctx = PassExecutionContext(
            gl=self.ctx,
            frame=frame,
            graph_resources=resources_map,
            gpu_resources=self.services.gpu_resources,
            resolution=(
                1920,
                1080,
            ),  # TODO: Get actual from Texture 0 or Window
        )

        for p in self.passes:
            p.execute(exec_ctx)

    def _create_resources(self, width: int, height: int) -> None:
        """
        Allocate GPU memory for all defined resources.
        """
        for rid, desc in self._tex_defs.items():
            w = desc.size[0] if desc.size else int(width * desc.size_scale)
            h = desc.size[1] if desc.size else int(height * desc.size_scale)

            # Simple wrapper mapping definition strings to ModernGL calls
            # TODO: handle MSAA and dtype parsing here.
            tex = self.ctx.texture((w, h), desc.components, dtype=desc.dtype)
            self._textures[rid] = tex

        for rid, desc in self._buf_defs.items():
            buf = self.ctx.buffer(reserve=desc.size_bytes, dynamic=desc.dynamic)
            self._buffers[rid] = buf

        for rid, desc in self._fbo_defs.items():
            colors = [self._textures[t_id] for t_id in desc.color_attachments]
            depth = (
                self._textures[desc.depth_attachment]
                if desc.depth_attachment
                else None
            )

            fbo = self.ctx.framebuffer(
                color_attachments=colors, depth_attachment=depth
            )
            self._framebuffers[rid] = fbo

    def destroy(self) -> None:
        """Cleanup GPU resources."""
        for t in self._textures.values():
            t.release()
        for b in self._buffers.values():
            b.release()
        for f in self._framebuffers.values():
            f.release()

        self._textures.clear()
        self._buffers.clear()
        self._framebuffers.clear()
