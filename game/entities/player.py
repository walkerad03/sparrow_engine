from typing import Optional
from xml.dom.minidom import Entity

from game.components.smooth_follow import SmoothFollow
from sparrow.core.components import BoxCollider, Sprite, Transform
from sparrow.core.world import World
from sparrow.graphics.light import PointLight
from sparrow.types import EntityId, Vector2


def create_player(
    world: World, x: float, y: float, z: float, eid: Optional[EntityId] = None
) -> EntityId:
    if eid is None:
        eid = world.create_entity()
    else:
        world.add_entity(eid)

    world.add_component(eid, Transform(x, y, z))
    world.add_component(
        eid,
        Sprite(
            texture_id="knight_f_idle_anim_f0",
            color=(1.0, 1.0, 1.0, 1.0),
            pivot=Vector2(0.5, 0.0),
            layer=3,
            skew=-1.0,
        ),
    )
    world.add_component(eid, BoxCollider(width=10, height=1, offset=(0, 0)))

    create_skull_light(world, x, y, z, parent_eid=eid)

    return eid


def create_skull_light(
    world: World, x: float, y: float, z: float, parent_eid: EntityId
) -> EntityId:
    eid = world.create_entity(
        Transform(x, y, z),
        Sprite(
            texture_id="skull",
            color=(1.0, 1.0, 1.0, 1.0),
            pivot=Vector2(0.5, 0.0),
            layer=3,
            skew=-1.0,
        ),
        PointLight((102 / 255, 153 / 255, 216 / 255), 150.0, True),
        SmoothFollow(
            parent_eid, 0, 0, 30, speed=1, wander_radius=10.0, wander_interval=2.0
        ),
    )

    return eid
