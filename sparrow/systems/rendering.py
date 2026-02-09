from __future__ import annotations

from sparrow.assets.server import AssetServer
from sparrow.core.world import World
from sparrow.graphics.core.renderer import Renderer
from sparrow.graphics.core.settings import RendererSettings
from sparrow.graphics.integration.frame import RenderFrame
from sparrow.resources.rendering import RenderContext, RendererResource


def render_system(world: World) -> None:
    frame_res = world.try_resource(RenderFrame)
    if frame_res is None:
        return

    renderer_res = ensure_renderer_resource(world)
    if renderer_res is None:
        return

    settings = world.try_resource(RendererSettings)
    if settings:
        renderer_res.renderer.update_settings(settings)

    renderer_res.renderer.render(frame_res)


def ensure_renderer_resource(world: World) -> RendererResource | None:
    renderer_res = world.try_resource(RendererResource)
    if renderer_res:
        return renderer_res

    ctx_res = world.try_resource(RenderContext)
    asset_server = world.try_resource(AssetServer)
    if not (ctx_res and asset_server):
        return None

    renderer = Renderer(ctx_res.gl, asset_server)

    renderer_res = RendererResource(renderer)
    world.add_resource(renderer_res)

    return renderer_res
