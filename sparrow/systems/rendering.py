from __future__ import annotations

from sparrow.assets.server import AssetServer
from sparrow.core.world import World
from sparrow.graphics.core.renderer import Renderer
from sparrow.graphics.core.settings import RendererSettings
from sparrow.graphics.integration.frame import RenderFrame
from sparrow.resources.rendering import RenderContext, RendererResource


def render_system(world: World) -> None:
    frame_res = world.resource_get(RenderFrame)
    if frame_res is None:
        return

    renderer_res = ensure_renderer_resource(world)
    if renderer_res is None:
        return

    settings = world.resource_get(RendererSettings)
    if settings:
        renderer_res.renderer.update_settings(settings)

    renderer_res.renderer.render(frame_res)


def ensure_renderer_resource(world: World) -> RendererResource | None:
    renderer_res = world.resource_get(RendererResource)
    if renderer_res:
        return renderer_res

    ctx_res = world.resource_get(RenderContext)
    asset_server = world.resource_get(AssetServer)
    if not (ctx_res and asset_server):
        return None

    renderer = Renderer(ctx_res.gl, asset_server)

    renderer_res = RendererResource(renderer)
    world.resource_add(renderer_res)

    return renderer_res
