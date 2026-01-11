from pygame import draw

from sparrow.core.components import Transform
from sparrow.core.world import World
from sparrow.graphics.components import Renderable
from sparrow.graphics.light import PointLight
from sparrow.graphics.renderer.draw_list import DrawItem, DrawLight, RenderDrawList


def build_draw_list_system(world: World) -> None:
    draw_list = RenderDrawList.empty()

    for eid, renderable, transform in world.join(Renderable, Transform):
        assert isinstance(renderable, Renderable) and isinstance(transform, Transform)

        item = DrawItem(
            eid=eid,
            renderable=renderable,
            position=transform.pos,
            rotation=transform.rot,
            scale=transform.scale,
        )

        if renderable.blend == "opaque":
            draw_list.opaque.append(item)
        else:
            draw_list.transparent.append(item)

    for eid, light, transform in world.join(PointLight, Transform):
        assert isinstance(light, PointLight) and isinstance(transform, Transform)

        item = DrawLight(
            position=transform.pos,
            color=(
                *light.color,
                1.0,
            ),
            radius=light.radius,
        )

        draw_list.lights.append(item)

    draw_list.opaque.sort(key=lambda i: i.renderable.sort_key)
    draw_list.transparent.sort(key=lambda i: i.renderable.sort_key)

    world.mutate_resource(draw_list)
