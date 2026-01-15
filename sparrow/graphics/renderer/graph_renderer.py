# sparrow/graphics/renderer/graph_renderer.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import moderngl

from sparrow.graphics.assets.material_manager import MaterialManager
from sparrow.graphics.assets.mesh_manager import MeshManager
from sparrow.graphics.assets.texture_manager import TextureManager
from sparrow.graphics.ecs.frame_submit import RenderFrameInput
from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.graph.compilation import compile_render_graph
from sparrow.graphics.graph.pass_base import RenderServices
from sparrow.graphics.graph.render_graph import CompiledRenderGraph
from sparrow.graphics.renderer.settings import RendererSettings
from sparrow.graphics.shaders.shader_manager import ShaderManager

# Define the Pipeline Strategy Signature
PipelineFactory = Callable[[RenderGraphBuilder, int, int], None]


@dataclass(slots=True)
class GraphRenderer:
    gl: moderngl.Context
    settings: RendererSettings

    # Managers (kept the same)
    _shader_mgr: ShaderManager | None = None
    _mesh_mgr: MeshManager | None = None
    _material_mgr: MaterialManager | None = None
    _texture_mgr: TextureManager | None = None

    _graph: CompiledRenderGraph | None = None

    def initialize(self) -> None:
        """Init managers but DO NOT build a default graph yet."""
        self._shader_mgr = ShaderManager(self.gl, include_paths=[])
        self._mesh_mgr = MeshManager(self.gl)
        self._material_mgr = MaterialManager()
        self._texture_mgr = TextureManager(self.gl)

    def set_pipeline(self, pipeline: PipelineFactory) -> None:
        """
        Switch the active render pipeline.
        """
        w = self.settings.resolution.logical_width
        h = self.settings.resolution.logical_height

        builder = RenderGraphBuilder()
        pipeline(builder, w, h)

        self._compile_and_activate(builder)

    def _compile_and_activate(self, builder: RenderGraphBuilder) -> None:
        if self._graph:
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
        self._graph = compile_render_graph(
            gl=self.gl, builder=builder, services=services
        )

    def render_frame(self, frame: RenderFrameInput) -> None:
        if self._graph:
            self._graph.execute(frame)
