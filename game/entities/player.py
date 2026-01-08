from sparrow.core.components import BoxCollider, Sprite, Transform
from sparrow.core.world import World
from sparrow.graphics.light import PointLight
from sparrow.types import EntityId


def create_player(world: World, x: float, y: float) -> EntityId:
    eid = world.create_entity(
        Transform(x=x, y=y, scale=1.0),
        Sprite(
            texture_id="wizard_robe",  # Placeholder ID
            color=(1.0, 0.2, 0.2, 1.0),  # Red
            layer=2,  # Actor layer
        ),
        BoxCollider(width=12, height=12),
        # The Lantern Light
        PointLight(
            radius=150.0, color=(1.0, 0.8, 0.5), intensity=2.0, cast_shadows=True
        ),
    )
    return eid
