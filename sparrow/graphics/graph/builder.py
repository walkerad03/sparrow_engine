# sparrow/graphics/graph/builder.py
from __future__ import annotations

from collections import OrderedDict
from typing import Dict

from sparrow.graphics.graph.definition import (
    BufferDesc,
    FramebufferDesc,
    TextureDesc,
)
from sparrow.graphics.graph.pass_base import RenderPass
from sparrow.graphics.utils.ids import PassId, ResourceId


class RenderGraphBuilder:
    """
    Accumulates passes and resource definitions to build the graph.
    """

    def __init__(self):
        self.passes: OrderedDict[PassId, RenderPass] = OrderedDict()
        self.textures: Dict[ResourceId, TextureDesc] = {}
        self.buffers: Dict[ResourceId, BufferDesc] = {}
        self.framebuffers: Dict[ResourceId, FramebufferDesc] = {}

    def add_pass(self, pass_instance: RenderPass) -> RenderGraphBuilder:
        """Add a new pass. Raises if pid already exists."""
        pid = pass_instance.pass_id
        if pid in self.passes:
            raise ValueError(f"Pass {pid} already exists.")
        self.passes[pid] = pass_instance
        return self

    def define_texture(
        self, rid: ResourceId, desc: TextureDesc
    ) -> RenderGraphBuilder:
        """Register or replace a texture resource description."""
        self.textures[rid] = desc
        return self

    def define_buffer(
        self, rid: ResourceId, desc: BufferDesc
    ) -> RenderGraphBuilder:
        """Register or replace a buffer resource description."""
        self.buffers[rid] = desc
        return self

    def define_framebuffer(
        self, rid: ResourceId, desc: FramebufferDesc
    ) -> RenderGraphBuilder:
        """Register or replace a buffer resource description."""
        self.framebuffers[rid] = desc
        return self
