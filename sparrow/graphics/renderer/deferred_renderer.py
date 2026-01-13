# sparrow/graphics/renderer/deferred_renderer.py
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Callable, Optional

import moderngl

from sparrow.graphics.assets.material_manager import MaterialManager
from sparrow.graphics.assets.mesh_manager import MeshManager
from sparrow.graphics.assets.texture_manager import TextureManager
from sparrow.graphics.debug.dump import dump_render_graph_state
from sparrow.graphics.ecs.frame_submit import RenderFrameInput
from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.graph.compilation import compile_render_graph
from sparrow.graphics.graph.pass_base import RenderServices
from sparrow.graphics.graph.render_graph import CompiledRenderGraph
from sparrow.graphics.renderer.settings import DeferredRendererSettings
from sparrow.graphics.shaders.shader_manager import ShaderManager

EventSink = Callable[[object], None]  # ECS event bus: emit(event)


@dataclass(slots=True)
class DeferredRenderer:
    """
    High-level deferred renderer.

    Responsibilities:
      - own shader/mesh/material/texture managers
      - own the render graph (builder + compiled graph)
      - provide a public API to modify/extend the graph
      - execute per-frame rendering using ECS-provided RenderFrameInput
      - emit renderer events back to ECS
    """

    gl: moderngl.Context
    settings: DeferredRendererSettings
    emit_event: Optional[EventSink] = None

    _shader_mgr: ShaderManager | None = None
    _mesh_mgr: MeshManager | None = None
    _material_mgr: MaterialManager | None = None
    _texture_mgr: TextureManager | None = None

    _builder: RenderGraphBuilder | None = None
    _graph: CompiledRenderGraph | None = None

    def initialize(self) -> None:
        """Initialize managers and build the default render graph."""
        self._shader_mgr = ShaderManager(self.gl, include_paths=[])
        self._mesh_mgr = MeshManager(self.gl)
        self._material_mgr = MaterialManager()
        self._texture_mgr = TextureManager(self.gl)

        builder = RenderGraphBuilder()
        self._activate_builder(builder, reason="initial")

    def rebuild_graph(
        self,
        configure: Callable[[RenderGraphBuilder], None],
        *,
        reason: str = "recompiled",
    ) -> None:
        """
        Rebuild and compile the render graph.

        `configure` is called with the graph builder to add/replace passes/resources.

        Emits RenderGraphChangedEvent if emit_event is configured.
        """
        base = self._clone_builder()
        configure(base)
        self._activate_builder(base, reason=reason)

    def render_frame(self, frame: RenderFrameInput) -> None:
        """
        Render a single frame.

        Emits RenderFrameEvent after completion if emit_event is configured.
        """
        if self._graph is None:
            raise RuntimeError("DeferredRenderer not initialized")

        self._graph.execute(frame)

    def _clone_builder(self) -> RenderGraphBuilder:
        """
        Clone current RenderGraphBuilder State.
        """
        assert isinstance(self._builder, RenderGraphBuilder)
        return deepcopy(self._builder)

    def _activate_builder(self, builder: RenderGraphBuilder, *, reason: str) -> None:
        """
        Activate a given RenderGraphBuilder.
        """
        if self._graph is not None:
            self._graph.destroy()

        assert self._shader_mgr is not None
        assert self._mesh_mgr is not None
        assert self._material_mgr is not None
        assert self._texture_mgr is not None

        services = RenderServices(
            shader_manager=self._shader_mgr,
            mesh_manager=self._mesh_mgr,
            material_manager=self._material_mgr,
            texture_manager=self._texture_mgr,
        )

        graph = compile_render_graph(gl=self.gl, builder=builder, services=services)

        self._builder = builder
        self._graph = graph

        dump_render_graph_state(
            graph=self._graph,
            gl=self.gl,
            header="POST-COMPILE GRAPH STATE",
        )

    @property
    def shader_manager(self) -> ShaderManager:
        """Access shader manager for advanced customization."""
        assert self._shader_mgr is not None
        return self._shader_mgr

    @property
    def mesh_manager(self) -> MeshManager:
        assert self._mesh_mgr is not None
        return self._mesh_mgr

    @property
    def material_manager(self) -> MaterialManager:
        assert self._material_mgr is not None
        return self._material_mgr

    @property
    def texture_manager(self) -> TextureManager:
        assert self._texture_mgr is not None
        return self._texture_mgr
