from __future__ import annotations

from sparrow.core.components import Sprite
from sparrow.core.world import World
from sparrow.graphics.components import Renderable
from sparrow.types import EntityId


def sprite_to_renderable_system(world: World) -> None:
    """
    Bridge system: Sprite → Renderable.

    Keeps gameplay-facing Sprite intact,
    but ensures renderer only sees Renderable.
    """
    to_add: list[EntityId] = []

    for eid, sprite in world.join(Sprite):
        if not world.has(eid, Renderable):
            to_add.append(eid)

    for eid in to_add:
        sprite = world.component(eid, Sprite)
        if sprite is None:
            continue

        world.add_component(
            eid,
            Renderable(
                mesh_id="quad",
                material=sprite.texture_id,
                domain="sprite",
                blend="alpha",
                sort_key=sprite.layer,
            ),
        )
