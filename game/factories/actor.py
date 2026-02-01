from game.components.boid import Boid
from game.components.enemy import Enemy
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
        Velocity(Vector2(0.0, 0.0)),
    )


def create_player(world: World, *, sx: float, sy: float) -> EntityId:
    eid = _create_actor(world)

    world.add_component(
        eid,
        Transform(
            pos=Vector3(sx, sy, 0.0),
            scale=Vector3(2, 2, 2),
        ),
    )

    world.add_component(
        eid,
        PolygonRenderable(
            vertices=[
                rotate_vec2(Vector2(0.0, 7.0), angle=deg_to_rad(0.0)),
                rotate_vec2(Vector2(0.0, 5.0), angle=deg_to_rad(120.0)),
                rotate_vec2(Vector2(0.0, 5.0), angle=deg_to_rad(240.0)),
            ],
            color=(1.0, 0.5, 1.0, 1.0),
            stroke_width=2.0,
            closed=True,
        ),
    )

    world.add_component(eid, Player())
    world.add_component(eid, RenderLayer(1))

    return eid


def create_enemy(world: World, *, sx: float, sy: float) -> EntityId:
    eid = _create_actor(world)

    world.add_component(
        eid,
        Transform(
            pos=Vector3(sx, sy, 0.0),
            scale=Vector3(1, 1, 1),
        ),
    )

    world.add_component(
        eid,
        PolygonRenderable(
            vertices=[
                rotate_vec2(Vector2(0.0, 7.0), angle=deg_to_rad(0.0)),
                rotate_vec2(Vector2(0.0, 5.0), angle=deg_to_rad(120.0)),
                rotate_vec2(Vector2(0.0, 5.0), angle=deg_to_rad(240.0)),
            ],
            color=(1.0, 0.0, 0.0, 1.0),
            stroke_width=2.0,
            closed=True,
        ),
    )

    world.add_component(eid, Enemy())
    world.add_component(
        eid,
        Boid(
            separation_weight=4.0,
            alignment_weight=0.2,
            cohesion_weight=0.8,
            target_weight=3.0,
            visual_range=250.0,
            protected_range=50.0,
        ),
    )
    world.add_component(eid, RenderLayer(1))

    return eid
