from sparrow.assets import AssetServer, DefaultMeshes
from sparrow.core import Transform, Velocity
from sparrow.ecs import World
from sparrow.graphics.integration import Mesh


def create_entities_system(world: World) -> None:
    for i in range(100_000):
        ent = world.entity_add()
        world.comp_add(
            ent,
            Transform(x=i * 10.0, y=0.0),
            Velocity(dx=1.0),
        )

    asset_server = world.res_get(AssetServer)
    if asset_server:
        mesh_handle = asset_server.load(DefaultMeshes.BUNNY)

    e = world.entity_add()
    world.comp_add(
        e,
        Transform(),
        Mesh(handle=mesh_handle),
    )
