# sparrow/graphics/graph/render_graph.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import moderngl

from sparrow.graphics.ecs.frame_submit import RenderFrameInput
from sparrow.graphics.graph.pass_base import (
    PassExecutionContext,
    RenderPass,
    RenderServices,
)
from sparrow.graphics.graph.resources import GraphResource
from sparrow.graphics.util.ids import PassId, ResourceId


@dataclass(slots=True)
class CompiledRenderGraph:
    """
    Executable render graph with a deterministic pass order and allocated resources.

    Instances should be treated as immutable except for per-frame execution.
    """

    gl: moderngl.Context
    pass_order: Sequence[PassId]
    passes: Mapping[PassId, RenderPass]
    resources: Mapping[ResourceId, GraphResource[object]]
    services: RenderServices  # shader/mesh/material managers

    def execute(self, frame: RenderFrameInput) -> None:
        """
        Execute all passes for the given frame.

        This does not do scene extraction; it assumes the caller has already
        assembled RenderFrameInput from ECS.
        """
        vp_w, vp_h = frame.viewport_width, frame.viewport_height
        if vp_w is None or vp_h is None:
            raise ValueError("viewport_width and viewport_frame must not be None")

        exec_ctx = PassExecutionContext(
            gl=self.gl,
            frame=frame,
            resources=self.resources,
            services=self.services,
            viewport_width=vp_w,
            viewport_height=vp_h,
        )

        for pid in self.pass_order:
            self.passes[pid].execute(exec_ctx)

    def destroy(self) -> None:
        """Destroy GPU resources and notify passes for cleanup."""
        for pid in self.pass_order:
            self.passes[pid].on_graph_destroyed()

        for res in self.resources.values():
            handle = getattr(res, "handle", None)
            if handle is not None:
                try:
                    handle.release()
                except Exception:
                    pass
