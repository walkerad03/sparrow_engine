from game.components.player import Player
from sparrow.core.components import (
    PolygonRenderable,
    RenderLayer,
    Transform,
    Velocity,
)
from sparrow.core.world import World
from sparrow.math import deg_to_rad, rotate_vec2
from sparrow.types import EntityId, Vector2, Vector3


def _create_actor(world: World) -> EntityId:
    return world.create_entity(
        Transform(pos=Vector3(500.0, 500.0, 0.0), scale=Vector3(2, 2, 2)),
        Velocity(Vector2(0.0, 0.0)),
    )


def create_player(world: World) -> EntityId:
    eid = _create_actor(world)

    world.add_component(
        eid,
        PolygonRenderable(
            vertices=[
                rotate_vec2(Vector2(0.0, 7.0), angle=deg_to_rad(0.0)),
                rotate_vec2(Vector2(0.0, 5.0), angle=deg_to_rad(120.0)),
                rotate_vec2(Vector2(0.0, 5.0), angle=deg_to_rad(240.0)),
            ],
            color=(1.0, 0.0, 1.0, 1.0),
            stroke_width=2.0,
            closed=True,
        ),
    )

    world.add_component(eid, Player())
    world.add_component(eid, RenderLayer(1))

    return eid
