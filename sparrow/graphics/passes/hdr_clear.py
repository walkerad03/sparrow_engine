# sparrow/graphics/passes/hdr_clear.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple, cast

import moderngl

from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
)
from sparrow.graphics.graph.resources import FramebufferResource
from sparrow.graphics.util.ids import PassId, ResourceId


@dataclass(slots=True)
class HdrClearPass(RenderPass):
    pass_id: PassId
    target: ResourceId
    color: Tuple[float, float, float, float] = (1.0, 0.0, 1.0, 1.0)

    _fbo_id: ResourceId | None = None

    def build(self) -> PassBuildInfo:
        return PassBuildInfo(
            pass_id=self.pass_id,
            name="HDR Clear",
            reads=[],
            writes=[
                PassResourceUse(
                    resource=self.target,
                    access="write",
                    stage="color",
                )
            ],
        )

    def on_graph_compiled(
        self,
        *,
        ctx: moderngl.Context,
        resources: Mapping[ResourceId, object],
        services: object,
    ) -> None:
        self._fbo_id = ResourceId(f"fbo:{self.pass_id}")

        if self._fbo_id not in resources:
            raise RuntimeError(f"Expected framebuffer resource '{self._fbo_id}'")

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        assert self._fbo_id

        fbo_res = cast(FramebufferResource, exec_ctx.resources[self._fbo_id])
        fbo = fbo_res.handle

        fbo.use()
        fbo.clear(
            red=self.color[0],
            green=self.color[1],
            blue=self.color[2],
            alpha=self.color[3],
        )

    def on_graph_destroyed(self) -> None:
        self._fbo_id = None
