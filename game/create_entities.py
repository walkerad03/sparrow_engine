import random

from sparrow.assets import AssetServer, DefaultMeshes
from sparrow.core import Transform, Velocity
from sparrow.ecs import World
from sparrow.graphics.integration import Camera, Mesh
from sparrow.types import Vector3


def create_entities_system(world: World) -> None:
    asset_server = world.res_get(AssetServer)
    if asset_server:
        mesh_handle = asset_server.load(DefaultMeshes.CUBE)

    for _ in range(100):
        e = world.entity_add()
        world.comp_add(
            e,
            Transform(
                pos=Vector3(
                    x=random.uniform(-10, 10),
                    y=random.uniform(-10, 10),
                    z=random.uniform(-10, 10),
                ),
                scale=Vector3(x=1, y=1, z=1),
            ),
            Velocity(),
            Mesh(handle=mesh_handle),
        )

    cam = world.entity_add()
    world.comp_add(
        cam,
        Transform(pos=Vector3(0.0, 2.0, 8.0)),
        Camera(active=True),
    )
