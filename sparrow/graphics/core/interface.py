from typing import Any, Callable

from sparrow.graphics.core.renderer import Renderer
from sparrow.graphics.graph.builder import RenderGraphBuilder


class RendererAPI:
    """
    Public API for the Renderer.
    Used by the Editor or Scripts to manipulate the pipeline.
    """

    def __init__(self, renderer: Renderer):
        self._renderer = renderer

    def reload_pipeline(
        self, setup_fn: Callable[[RenderGraphBuilder], None]
    ) -> None:
        """Hot-swap the entire rendering pipeline."""
        self._renderer.set_pipeline(setup_fn)

    def get_stats(self) -> dict[str, Any]:
        """Return frame timings and memory usage."""
        # TODO: This should hook into a FrameContext or Profiler
        raise NotImplementedError

    def capture_screenshot(self, path: str) -> None:
        """Request a screenshot of the next frame."""
        raise NotImplementedError
