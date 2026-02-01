import math
import random

from game.components.spaceship import ShipTrail
from game.components.star import Star
from sparrow.core.components import (
    Lifetime,
    PolygonRenderable,
    RenderLayer,
    Transform,
    Velocity,
)
from sparrow.core.world import World
from sparrow.math import dist_vec, rotate_vec2
from sparrow.types import EntityId, Scalar, Vector2, Vector3


def create_star(world: World, max_range: Vector2) -> EntityId:
    depth = random.uniform(0, 1)
    px, py = (
        random.uniform(-100, 100 + max_range.x),
        random.uniform(-100, 100 + max_range.y),
    )
    eid = world.create_entity(
        Transform(
            pos=Vector3(px, py, 0),
            scale=Vector3(depth, depth, -1),
        ),
        PolygonRenderable(
            vertices=[
                Vector2(-1.0, -1.0),
                Vector2(1.0, -1.0),
                Vector2(1.0, 1.0),
                Vector2(1.0, -1.0),
            ],
            color=(1.0, 1.0, 1.0, depth),
            stroke_width=max(1.0, 1 - depth * 3),
            closed=True,
        ),
        RenderLayer(-10),
        Star(),
    )

    return eid


def create_bullet(
    world: World, *, pos: Vector2, speed: Scalar, angle: Scalar
) -> EntityId:
    b_dir = rotate_vec2(Vector2(0.0, 1.0), angle=angle + (math.pi / 2))
    b_vel = b_dir * speed

    return world.create_entity(
        Transform(pos=Vector3(pos.x, pos.y, 0.0)),
        Velocity(b_vel),
        PolygonRenderable(
            [
                rotate_vec2(Vector2(0, -3), angle + (math.pi / 2)),
                rotate_vec2(Vector2(0, 3), angle + (math.pi / 2)),
            ],
            (255, 0, 0, 1.0),
            1.0,
            False,
        ),
        Lifetime(1.5),
        RenderLayer(3),
    )


def create_spaceship_trail(
    world: World, *, pos_a: Vector2, pos_b: Vector2
) -> EntityId:
    speed = dist_vec(pos_a, pos_b) * 50.0
    intensity = min(speed * 0.5, 1.0)
    trail_color = (0.0, intensity, intensity, 1.0)

    return world.create_entity(
        Transform(),
        PolygonRenderable(
            [pos_a, pos_b],
            trail_color,
            2.0,
            False,
        ),
        Lifetime(0.5),
        RenderLayer(0),
        ShipTrail(),
    )
