# sparrow/graphics/api/renderer_api.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.graph.pass_base import RenderPass
from sparrow.graphics.graph.resources import BufferDesc, TextureDesc
from sparrow.graphics.renderer.deferred_renderer import DeferredRenderer
from sparrow.graphics.util.ids import PassId, ResourceId


@dataclass(slots=True)
class GraphEdit:
    """
    Mutable graph edit session.

    Apply changes via methods, then call commit() to compile and activate.
    """

    _api: RendererAPI
    _builder: RenderGraphBuilder
    _reason: str = "recompiled"
    _committed: bool = False

    def add_texture(self, rid: ResourceId, desc: TextureDesc) -> None:
        """Add or replace a texture resource."""
        self._builder.add_texture(rid, desc)

    def add_buffer(self, rid: ResourceId, desc: BufferDesc) -> None:
        """Add or replace a buffer resource."""
        self._builder.add_buffer(rid, desc)

    def add_pass(self, pid: PassId, pass_obj: RenderPass) -> None:
        """Add a new pass."""
        self._builder.add_pass(pid, pass_obj)

    def replace_pass(self, pid: PassId, pass_obj: RenderPass) -> None:
        """Replace an existing pass."""
        self._builder.replace_pass(pid, pass_obj)

    def remove_pass(self, pid: PassId) -> None:
        """Remove a pass."""
        self._builder.remove_pass(pid)

    def commit(self, *, reason: Optional[str] = None) -> None:
        """
        Compile and activate the edited graph.

        Args:
            reason: Optional reason string for RenderGraphChangedEvent.
        """
        if self._committed:
            raise RuntimeError("GraphEdit already committed.")
        self._committed = True
        self._api._commit_builder(self._builder, reason=reason or self._reason)


@dataclass(slots=True)
class RendererAPI:
    """
    Public API surface for modifying the renderer.

    This is the intended integration point for:
      - editor tooling
      - mods / scripting
      - engine feature modules (SSR, SSAO, VSM, TAA, etc.)
    """

    renderer: DeferredRenderer

    def configure_graph(
        self,
        configure: Callable[[RenderGraphBuilder], None],
        *,
        reason: str = "recompiled",
    ) -> None:
        """
        Apply graph modifications and force compilation.

        Example usage:
            api.configure_graph(lambda g: g.replace_pass(PassId("lighting"), MyLightingPass(...)))
        """
        self.renderer.rebuild_graph(configure, reason=reason)

    def rebuild_default_graph(self) -> None:
        """Rebuild the default pass set (gbuffer -> lighting -> tonemap)."""
        ...

    def begin_graph_edit(self, *, reason: str = "recompiled") -> GraphEdit:
        """
        Begin a graph edit session.

        Returns:
            GraphEdit: An object used to apply graph modifications and commit them.
        """
        builder = self.renderer._clone_builder()
        return GraphEdit(_api=self, _builder=builder, _reason=reason)

    def _commit_builder(self, builder: RenderGraphBuilder, *, reason: str) -> None:
        """Internal commit hook used by GraphEdit."""
        self.renderer._activate_builder(builder, reason=reason)
