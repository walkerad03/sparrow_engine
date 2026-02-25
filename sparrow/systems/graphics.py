import logging

from sparrow.ecs.world import World
from sparrow.graphics.core.renderer import Renderer
from sparrow.graphics.integration.frame import RenderFrame

logger = logging.getLogger("sparrow.graphics")


def graphics_system(world: World) -> None:
    renderer = world.res_get(Renderer)
    frame = world.res_get(RenderFrame)

    if not (renderer and frame):
        return

    renderer.render(frame)
