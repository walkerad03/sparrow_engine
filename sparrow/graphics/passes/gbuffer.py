# sparrow/graphics/passes/gbuffer.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import moderngl

from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassExecutionContext,
    RenderPass,
    RenderServices,
)
from sparrow.graphics.graph.resources import GraphResource
from sparrow.graphics.util.ids import PassId, ResourceId


@dataclass(slots=True)
class GBufferPass(RenderPass):
    """
    Fills GBuffer attachments from opaque geometry.

    Typical outputs:
      - g_albedo (rgba8 or rgba16f)
      - g_normal (rgba16f)
      - g_orm    (rgba8/rgba16f)
      - g_depth  (depth24/depth32f)
    """

    pass_id: PassId
    gbuffer_fbo: ResourceId
    g_albedo: ResourceId
    g_normal: ResourceId
    g_orm: ResourceId
    g_depth: ResourceId

    def build(self) -> PassBuildInfo:
        """Declare GBuffer attachments as writes; may read material textures."""
        raise NotImplementedError

    def on_graph_compiled(
        self,
        *,
        ctx: moderngl.Context,
        resources: Mapping[ResourceId, GraphResource[object]],
        services: RenderServices,
    ) -> None:
        """Compile GBuffer shader program and cache uniform/attrib locations."""
        ...

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        """Render draw list into the GBuffer framebuffer."""
        ...

    def on_graph_destroyed(self) -> None:
        """Release any cached state owned by the pass (if applicable)."""
        ...
