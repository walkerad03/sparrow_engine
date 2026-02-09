# sparrow/graphics/core/renderer.py
from typing import Callable, Optional

import moderngl

from sparrow.assets.server import AssetServer
from sparrow.graphics.core.settings import RendererSettings
from sparrow.graphics.graph import GraphExecutor
from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.graph.pass_base import RenderServices
from sparrow.graphics.integration.frame import RenderFrame
from sparrow.graphics.resources.manager import GPUResourceManager
from sparrow.graphics.resources.shader import ShaderManager


class Renderer:
    def __init__(self, ctx: moderngl.Context, asset_server: AssetServer):
        self.ctx = ctx
        self._settings = RendererSettings()  # Default will be overwritten

        self.gpu_resources = GPUResourceManager(ctx, asset_server)
        self.shader_manager = ShaderManager(ctx)

        self._executor: Optional[GraphExecutor] = None
        self._builder: Optional[RenderGraphBuilder] = None

    def update_settings(self, settings: RendererSettings) -> None:
        """Called by the System to sync ECS settings to Renderer."""
        self._settings = settings
        # NOTE: Could trigger resize logic here if resolution changes

    def set_pipeline(
        self, setup_fn: Callable[[RenderGraphBuilder], None]
    ) -> None:
        """
        Recompile the render graph using the provided setup function.
        """
        builder = RenderGraphBuilder()
        setup_fn(builder)

        if self._executor:
            self._executor.destroy()

        services = RenderServices(
            shader_manager=self.shader_manager,
            gpu_resources=self.gpu_resources,
            # Material manager handles are now resolved via gpu_resources
        )

        self._executor = GraphExecutor(self.ctx, builder, services)
        self._builder = builder

    def render(self, frame: RenderFrame) -> None:
        """
        Main render loop.
        """
        self.gpu_resources.sync()

        if self._executor:
            self._executor.execute(frame)
        else:
            self.ctx.clear(1.0, 0.0, 1.0, 1.0)
