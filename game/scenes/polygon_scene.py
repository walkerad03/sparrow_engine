import random

import numpy as np

from game.factories.actor import create_enemy, create_player
from game.factories.game_object import create_star
from game.systems.boid import boid_system
from game.systems.player_controller import player_controller_system
from game.systems.starfield_system import starfield_system
from game.systems.trails import trail_vfx_system
from sparrow.core.application import Application
from sparrow.core.components import Camera, Transform
from sparrow.core.scene import Scene
from sparrow.core.scheduler import Stage
from sparrow.graphics.renderer.settings import (
    PolygonRendererSettings,
    ResolutionSettings,
    SunlightSettings,
)
from sparrow.resources.rendering import RendererSettingsResource
from sparrow.types import Vector2


class PolygonScene(Scene):
    def __init__(self, app: Application):
        self.w, self.h = 1920, 1080

        self.settings = PolygonRendererSettings(
            ResolutionSettings(
                logical_width=self.w,
                logical_height=self.h,
            ),
            SunlightSettings(),
        )

        super().__init__(app, renderer_settings=self.settings)

    def on_start(self):
        self.scheduler.add_system(Stage.UPDATE, player_controller_system)
        self.scheduler.add_system(Stage.POST_UPDATE, trail_vfx_system)
        self.scheduler.add_system(Stage.UPDATE, starfield_system)
        self.scheduler.add_system(Stage.UPDATE, boid_system)

        self.world.add_resource(RendererSettingsResource(self.settings))

        self.world.create_entity(
            Transform(),
            Camera(
                fov=70.0,
                width=self.w,
                height=self.h,
                near_clip=0.1,
                far_clip=100.0,
                target=np.array([0.0, 0.0, 0.0]),
            ),
        )

        create_player(self.world, sx=500, sy=500)

        for _ in range(100):
            create_star(self.world, Vector2(self.w, self.h))

        for _ in range(100):
            sx = random.uniform(0, self.w)
            sy = random.uniform(0, self.h)
            create_enemy(self.world, sx=sx, sy=sy)

        super().on_start()

    def on_update(self):
        super().on_update()

    def get_render_frame(self):
        return super().get_render_frame()
