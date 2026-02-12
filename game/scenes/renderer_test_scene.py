# game/scenes/renderer_test_scene.py

import numpy as np
import pygame

from sparrow.assets import AssetServer, DefaultMeshes
from sparrow.core.components import Transform
from sparrow.core.query import Query
from sparrow.core.scene import Scene
from sparrow.core.scheduler import Stage
from sparrow.core.world import World
from sparrow.graphics.integration import (
    Camera,
    DirectionalLight,
    Material,
    Mesh,
)
from sparrow.graphics.pipelines import build_standard_3d_pipeline
from sparrow.resources.core import SimulationTime
from sparrow.systems.rendering import ensure_renderer_resource
from sparrow.types import Quaternion, Vector3


def rotation_system(world: World) -> None:
    """Simple system to rotate objects."""
    sim = world.resource_get(SimulationTime)
    t = sim.elapsed_seconds if sim else 0.0

    for count, (trans_view, mesh_view) in Query(world, Transform, Mesh):
        trans_view.rot[:] = Quaternion.from_euler(t * 32, 0, 0)
        trans_view.pos.y[:] = np.sin(t * 10) * 0.5


class Test3DScene(Scene):
    def on_start(self):
        print("Starting Test 3D Scene...")

        if not self.world.resource_get(AssetServer):
            self.world.resource_add(self.app.asset_server)

        renderer_res = ensure_renderer_resource(self.world)

        if renderer_res:
            renderer_res.renderer.set_pipeline(build_standard_3d_pipeline)

        mesh_handle = self.app.asset_server.load(DefaultMeshes.BUNNY)

        for x in range(-20, 22, 2):
            for z in range(-80, 20, 2):
                self.world.entity_spawn(
                    Transform(pos=Vector3(x, 0.0, z - 5)),
                    Mesh(handle=mesh_handle),
                    Material(base_color=(1.0, 0.5, 0.2, 1.0)),
                )

        self.world.entity_spawn(
            Transform(
                pos=Vector3(0, 2, 9),
                rot=Quaternion(0, 0, 0, 1),
            ),
            Camera(fov=60.0, near=0.1, far=100.0, active=True),
        )

        self.world.entity_spawn(
            Transform(),
            DirectionalLight(color=(1.0, 0.9, 0.8), intensity=1.5),
        )

        self.scheduler.add_system(Stage.UPDATE, rotation_system)

        super().on_start()

        pygame.mixer.init()

        song = pygame.mixer.Sound(file="oiia.mp3")
        song.set_volume(1)
        song.play(loops=True)

    def on_update(self):
        super().on_update()
