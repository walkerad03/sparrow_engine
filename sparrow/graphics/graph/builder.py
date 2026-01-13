# sparrow/graphics/graph/builder.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from sparrow.graphics.graph.pass_base import RenderPass
from sparrow.graphics.graph.resources import BufferDesc, FramebufferDesc, TextureDesc
from sparrow.graphics.util.ids import PassId, ResourceId


@dataclass(slots=True)
class RenderGraphBuilder:
    """
    Mutable builder used by the public API to add/replace passes and resources.

    Typical flow:
        - declare resources (gbuffer textures, depth, light accumulation, etc.)
        - add passes referencing those resources
        - compile into an executable graph

    All correctness checks beyond basic existence belong in graph compilation.
    """

    textures: Dict[ResourceId, TextureDesc] = field(default_factory=dict)
    buffers: Dict[ResourceId, BufferDesc] = field(default_factory=dict)
    framebuffers: Dict[ResourceId, FramebufferDesc] = field(default_factory=dict)
    passes: Dict[PassId, RenderPass] = field(default_factory=dict)

    def add_texture(self, rid: ResourceId, desc: TextureDesc) -> None:
        """Register or replace a texture resource description."""
        self.textures[rid] = desc

    def add_buffer(self, rid: ResourceId, desc: BufferDesc) -> None:
        """Register or replace a buffer resource description."""
        self.buffers[rid] = desc

    def add_framebuffer(self, rid: ResourceId, desc: FramebufferDesc) -> None:
        """Register or replace a buffer resource description."""
        self.framebuffers[rid] = desc

    def add_pass(self, pid: PassId, pass_obj: RenderPass) -> None:
        """Add a new pass. Raises if pid already exists (use replace_pass)."""
        if pid in self.passes:
            raise KeyError(f"Pass '{pid}' already exists (use replace_pass)")

        self.passes[pid] = pass_obj

    def replace_pass(self, pid: PassId, pass_obj: RenderPass) -> None:
        """Replace an existing pass implementation under the same id."""
        if pid not in self.passes:
            raise KeyError(f"Cannot replace non-existent pass '{pid}'")

        self.passes[pid] = pass_obj

    def remove_pass(self, pid: PassId) -> None:
        """Remove a pass by id."""
        if pid not in self.passes:
            raise KeyError(f"Cannot remove non-existent pass '{pid}'")

        del self.passes[pid]

    def remove_resource(self, rid: ResourceId) -> None:
        """Remove a resource (must not be referenced by remaining passes)."""
        if rid in self.textures:
            del self.textures[rid]
            return

        if rid in self.buffers:
            del self.buffers[rid]
            return

        if rid in self.framebuffers:
            del self.framebuffers[rid]
            return

        raise KeyError(f"Resource '{rid}' does not exist")
