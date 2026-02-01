import random
from dataclasses import replace
from typing import reveal_type

from game.factories.actor import create_enemy, create_player
from game.factories.game_object import create_star
from game.systems.boid import boid_system
from game.systems.player_controller import player_controller_system
from game.systems.starfield_system import starfield_system
from game.systems.trails import trail_vfx_system
from sparrow.core.application import Application
from sparrow.core.components import Camera2D, Transform, Velocity
from sparrow.core.scene import Scene
from sparrow.core.scheduler import Stage
from sparrow.graphics.renderer.settings import (
    PolygonRendererSettings,
    ResolutionSettings,
    SunlightSettings,
)
from sparrow.math import magnitude_vec
from sparrow.resources.rendering import RendererSettingsResource
from sparrow.types import Vector2, Vector3


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

        self.cid = self.world.create_entity(
            Transform(pos=Vector3(960, 540, 0)),
            Camera2D(
                zoom=1080.0,
                width=self.w,
                height=self.h,
                near_clip=-100.0,
                far_clip=100.0,
            ),
        )

        self.pid = create_player(self.world, sx=500, sy=500)

        for _ in range(100):
            create_star(self.world, Vector2(self.w, self.h))

        for _ in range(100):
            sx = random.uniform(0, self.w)
            sy = random.uniform(0, self.h)
            create_enemy(self.world, sx=sx, sy=sy)

        super().on_start()

    def on_update(self):
        p_trans = self.world.component(self.pid, Transform)
        p_vel = self.world.component(self.pid, Velocity)
        c_trans = self.world.component(self.cid, Transform)
        c_cam = self.world.component(self.cid, Camera2D)

        if p_trans and p_vel and c_trans and c_cam:
            p_pos = p_trans.pos
            c_pos = c_trans.pos

            t = 0.3
            t2 = 0.01
            new_c_pos = c_pos * (1 - t) + p_pos * t
            target_zoom = min(2000, max(500, magnitude_vec(p_vel.vec) * 2))
            current_zoom = c_cam.zoom

            new_zoom = current_zoom * (1 - t2) + target_zoom * t2

            self.world.mutate_component(
                self.cid, replace(c_trans, pos=new_c_pos)
            )
            self.world.mutate_component(self.cid, replace(c_cam, zoom=new_zoom))

        super().on_update()

    def get_render_frame(self):
        return super().get_render_frame()
