from sparrow.assets import AssetServer, DefaultMeshes
from sparrow.core import Transform, Velocity
from sparrow.ecs import World
from sparrow.graphics.integration import Mesh


def create_entities_system(world: World) -> None:
    asset_server = world.res_get(AssetServer)
    if asset_server:
        mesh_handle = asset_server.load(DefaultMeshes.DRAGON_DECIMATED)

    e = world.entity_add()
    world.comp_add(
        e,
        Transform(),
        Velocity(),
        Mesh(handle=mesh_handle),
    )
