from __future__ import annotations

from sparrow.core.world import World
from sparrow.graphics.renderer.renderer import Renderer
from sparrow.resources.rendering import (
    RenderContext,
    RenderFrame,
    RendererResource,
    RendererSettingsResource,
)


def ensure_renderer_resource(world: World) -> RendererResource | None:
    renderer_res = world.try_resource(RendererResource)
    if renderer_res is not None:
        return renderer_res

    ctx_res = world.try_resource(RenderContext)
    settings_res = world.try_resource(RendererSettingsResource)
    if ctx_res is None or settings_res is None:
        return None

    renderer = Renderer(ctx_res.gl, settings_res.settings)
    renderer.initialize()

    renderer_res = RendererResource(renderer)
    world.add_resource(renderer_res)
    return renderer_res


def render_system(world: World) -> None:
    frame_res = world.try_resource(RenderFrame)
    if frame_res is None:
        return

    renderer_res = ensure_renderer_resource(world)
    if renderer_res is None:
        return

    renderer_res.renderer.render_frame(frame_res.frame)
