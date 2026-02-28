from game.black_hole_pipeline import OUTER_DISC_RADIUS
from game.freecam import FreeCamConfig
from sparrow.core import Transform
from sparrow.ecs import World
from sparrow.graphics.integration import Camera
from sparrow.spatial.spatial_index import SpatialIndex
from sparrow.types import Vector3


def create_black_hole_scene_system(world: World) -> None:
    world.res_add(SpatialIndex(cell_size=200.0))

    existing_cameras = world.query(Camera, Transform)
    if len(existing_cameras) > 0:
        return

    cam_distance = OUTER_DISC_RADIUS * 1.45
    camera_entity = world.entity_add()
    world.comp_add(
        camera_entity,
        Transform(
            pos=Vector3(
                0.0,
                OUTER_DISC_RADIUS * 1.5,
                cam_distance,
            )
        ),
        Camera(
            active=True,
            fov=40.0,
            near=0.01,
            far=50000.0,
        ),
    )

    world.res_add(
        FreeCamConfig(
            move_speed=2.0,
            look_sensitivity=0.0020,
        )
    )
