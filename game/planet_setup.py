from game.atmosphere_pipeline import PLANET_RADIUS
from game.freecam import FreeCamConfig
from sparrow.core import Transform
from sparrow.ecs import World
from sparrow.graphics.integration import Camera
from sparrow.spatial.spatial_index import SpatialIndex
from sparrow.types import Vector3


def create_planet_scene_system(world: World) -> None:
    world.res_add(SpatialIndex(cell_size=PLANET_RADIUS * 20.0))

    existing_cameras = world.query(Camera, Transform)
    if len(existing_cameras) > 0:
        return

    camera_entity = world.entity_add()
    world.comp_add(
        camera_entity,
        Transform(
            pos=Vector3(
                0.0,
                PLANET_RADIUS * 0.025,
                PLANET_RADIUS * 1.13,
            )
        ),
        Camera(
            active=True,
            fov=55.0,
            near=1.0,
            far=PLANET_RADIUS * 30.0,
        ),
    )

    world.res_add(
        FreeCamConfig(
            move_speed=PLANET_RADIUS * 0.18,
            look_sensitivity=0.0025,
        )
    )
