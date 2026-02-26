import random

from sparrow.assets import AssetServer, DefaultMeshes
from sparrow.core import Transform
from sparrow.ecs import World
from sparrow.graphics.integration import Camera, Material, Mesh
from sparrow.types import Vector3


def make_test_entity(world: World) -> int:
    asset_server = world.res_get(AssetServer)
    if asset_server:
        mesh_handle = asset_server.load(DefaultMeshes.SPHERE)

    eid = world.entity_add()

    rand_scale = random.uniform(0, 1)

    world.comp_add(
        eid,
        Transform(
            pos=Vector3(
                x=random.uniform(-50, 50),
                y=random.uniform(1, 50),
                z=random.uniform(-50, 50),
            ),
            scale=Vector3(x=rand_scale, y=rand_scale, z=rand_scale),
        ),
        Mesh(handle=mesh_handle),
        Material(base_color=(random.uniform(0, 255), 1.0, 1.0, 1.0)),
    )

    return eid


def make_floor(world: World) -> int:
    asset_server = world.res_get(AssetServer)
    if asset_server:
        mesh_handle = asset_server.load(DefaultMeshes.PLANE)

    eid = world.entity_add()
    world.comp_add(
        eid,
        Transform(
            scale=Vector3(x=20, y=1, z=20),
        ),
        Mesh(handle=mesh_handle),
        Material(base_color=(random.uniform(0, 1), 1.0, 1.0, 1.0)),
    )

    return eid


def create_entities_system(world: World) -> None:
    for _ in range(100):
        make_test_entity(world)

    make_floor(world)

    cam = world.entity_add()
    world.comp_add(
        cam,
        Transform(pos=Vector3(0.0, 2.0, 8.0)),
        Camera(active=True),
    )
