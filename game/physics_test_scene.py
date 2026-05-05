import random

import numpy as np
import pybullet as p

from game.freecam import freecam_system
from game.input import SpawnCubeRequest, game_input_system
from game.n_body_gravity import GravityPointSource, n_body_gravity_system
from game.physics_grab import physics_grab_system
from sparrow.assets import AssetServer, DefaultMeshes
from sparrow.core import Scene, Stage, Transform
from sparrow.ecs import World
from sparrow.graphics.core.renderer import Renderer
from sparrow.graphics.integration import (
    Camera,
    DirectionalLight,
    Material,
    Mesh,
)
from sparrow.graphics.pipelines.standard_3d import build_standard_3d_pipeline
from sparrow.network.client import EngineNetworkClient
from sparrow.physics.components import Collider, RigidBody
from sparrow.types import Quaternion, SystemId, Vector3

# Using DefaultMeshes enum for correct relative paths
CUBE_MODEL_PATH = DefaultMeshes.CUBE
PLANE_MODEL_PATH = DefaultMeshes.PLANE


class PhysicsTestScene(Scene):
    def __init__(self):
        super().__init__(id="physics_test_scene")

        # Setup entities
        self.scheduler.add_system(Stage.SETUP, create_physics_test_entities)

        self.scheduler.add_system(
            Stage.FIXED_UPDATE,
            game_input_system,
            name=SystemId("game_input"),
            before=SystemId("input_system"),
        )
        self.scheduler.add_system(Stage.FIXED_UPDATE, freecam_system)
        self.scheduler.add_system(Stage.FIXED_UPDATE, physics_grab_system)
        self.scheduler.add_system(Stage.FIXED_UPDATE, physics_test_spawn_system)
        self.scheduler.add_system(Stage.FIXED_UPDATE, n_body_gravity_system)

    def setup(self, world: World) -> None:
        renderer = world.res_get(Renderer)
        if renderer:
            # Explicitly set the standard 3D pipeline
            renderer.set_pipeline(build_standard_3d_pipeline)

        net_client = EngineNetworkClient(world=world)
        net_client.connect_to("127.0.0.1", 5071)
        world.res_add(net_client)

        super().setup(world)


def physics_test_spawn_system(world: World) -> None:
    """Spawns a rigid body cube when a SpawnCubeRequest event is received."""
    for _ in world.event_get(SpawnCubeRequest):
        view = world.query(Camera, Transform)
        if len(view) == 0:
            continue

        # Find the active camera
        cam_idx = -1
        for i in range(len(view)):
            if view.Camera.active[i]:
                cam_idx = i
                break

        if cam_idx == -1:
            continue

        cam_pos = view.Transform.pos[cam_idx]
        cam_rot = view.Transform.rot[cam_idx]

        # Calculate forward vector from quaternion
        def rotate_vec(v, q):
            # v is (x, y, z), q is (x, y, z, w)
            # Standard quaternion rotation: v' = v + 2 * q_vec x (q_vec x v + q_w * v)
            q_vec = np.array([q[0], q[1], q[2]], dtype="f4")
            q_w = q[3]
            uv = np.cross(q_vec, v)
            uuv = np.cross(q_vec, uv)
            return v + 2 * (q_w * uv + uuv)

        forward = rotate_vec(np.array([0, 0, -1], dtype="f4"), cam_rot)
        spawn_pos = cam_pos + forward * 5.0

        # Spawn the cube
        asset_server = world.res_get(AssetServer)
        if not asset_server:
            return

        cube_mesh = asset_server.load(CUBE_MODEL_PATH)

        eid = world.entity_add()
        world.comp_add(
            eid,
            Transform(
                pos=Vector3(
                    spawn_pos[0] + random.uniform(-0.05, 0.05),
                    spawn_pos[1] + random.uniform(-0.05, 0.05),
                    spawn_pos[2] + random.uniform(-0.05, 0.05),
                ),
                rot=cam_rot,
                scale=Vector3(1.0, 1.0, 1.0),
            ),
            Mesh(handle=cube_mesh),
            Material(
                base_color=(random_color()),
                roughness=0.2,
                metallic=random.uniform(0, 1),
            ),
            RigidBody(mass=10.0),
            Collider(shape_type=p.GEOM_BOX, extents=Vector3(1, 1, 1)),
            GravityPointSource(),
        )


def random_color():
    return (random.random(), random.random(), random.random(), 1.0)


def create_physics_test_entities(world: World) -> None:
    asset_server = world.res_get(AssetServer)
    if not asset_server:
        return

    plane_mesh = asset_server.load(PLANE_MODEL_PATH)

    # Spawn Plane (Static)
    plane_eid = world.entity_add()
    world.comp_add(
        plane_eid,
        Transform(
            pos=Vector3(0.0, -2.0, 0.0), scale=Vector3(100.0, 1.0, 100.0)
        ),
        Mesh(handle=plane_mesh),
        Material(base_color=(0.5, 0.5, 0.5, 1.0), roughness=0.1),
        RigidBody(mass=0.0),  # mass 0 = static in PyBullet
        Collider(shape_type=p.GEOM_BOX, extents=Vector3(100.0, 0.1, 100.0)),
    )

    # Add a light so things aren't just ambiently lit
    sun_eid = world.entity_add()
    sun_rot = Quaternion.from_euler(
        pitch=np.radians(60.0), yaw=np.radians(45.0), roll=0.0
    )
    world.comp_add(
        sun_eid,
        Transform(
            pos=Vector3(10, 20, 10),
            rot=sun_rot,
        ),
        DirectionalLight(color=(0.95, 0.91, 0.6), intensity=2.0),
    )

    # Spawn initial camera
    cam = world.entity_add()
    world.comp_add(
        cam,
        Transform(pos=Vector3(0.0, 10.0, 30.0)),
        Camera(active=True, far=1000.0),
        RigidBody(mass=1.0, is_kinematic=True),
        Collider(shape_type=p.GEOM_BOX, extents=Vector3(1, 1, 1)),
    )
