# sparrow/graphics/passes/lighting_deffered.py
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
class DeferredLightingPass(RenderPass):
    """
    Full-screen deferred lighting.

    Reads:
        - GBuffer textures (albedo, normal, orm, depth)
    Writes:
        - light_accum texture (hdr)
    """

    pass_id: PassId
    out_fbo: ResourceId
    light_accum: ResourceId
    g_albedo: ResourceId
    g_normal: ResourceId
    g_orm: ResourceId
    g_depth: ResourceId

    def build(self) -> PassBuildInfo:
        raise NotImplementedError

    def on_graph_compiled(
        self,
        *,
        ctx: moderngl.Context,
        resources: Mapping[ResourceId, GraphResource[object]],
        services: RenderServices,
    ) -> None:
        """Compile fullscreen lighting shader; setup uniform blocks for light lists if desired."""
        ...

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        """Bind GBuffer textures and render a fullscreen triangle."""
        ...

    def on_graph_destroyed(self) -> None: ...
