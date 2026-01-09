from sparrow.core.components import BoxCollider, Sprite, Transform
from sparrow.core.world import World
from sparrow.graphics.light import PointLight, BlocksLight
from sparrow.types import EntityId


def create_player(world: World, x: float, y: float) -> EntityId:
    eid = world.create_entity(
        Transform(x=x, y=y, scale=1.0),
        Sprite(
            texture_id="goblin_idle_anim_f0",  # Placeholder ID
            color=(1.0, 1.0, 1.0, 1.0),
            layer=2,  # Actor layer
        ),
        BoxCollider(width=8, height=8),
        # The Lantern Light
        PointLight(
            radius=150.0, color=(1.0, 0.8, 0.5), intensity=2.0, cast_shadows=True
        ),
    )
    return eid


def create_ghost(world: World, eid: int, x: float, y: float) -> None:
    world.add_entity(
        EntityId(eid),
        Transform(x=x, y=y, scale=1.0),
        Sprite(
            texture_id="goblin_idle_anim_f0",  # Placeholder ID
            color=(1.0, 1.0, 1.0, 1.0),
            layer=2,  # Actor layer
        ),
        BoxCollider(width=8, height=8),
        # The Lantern Light
        PointLight(
            radius=150.0, color=(1.0, 0.8, 0.5), intensity=2.0, cast_shadows=True
        ),
    )
