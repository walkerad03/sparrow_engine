from sparrow.core.components import Transform
from sparrow.core.world import World
from sparrow.graphics.components import Renderable
from sparrow.graphics.renderer.draw_list import DrawItem, RenderDrawList


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

    draw_list.opaque.sort(key=lambda i: i.renderable.sort_key)
    draw_list.transparent.sort(key=lambda i: i.renderable.sort_key)

    world.mutate_resource(draw_list)
