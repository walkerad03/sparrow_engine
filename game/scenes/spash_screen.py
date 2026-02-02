# game/scenes/splash_screen.py
from game.factories.actor import create_player
from game.scenes.polygon_scene import PolygonScene
from sparrow.core.application import Application
from sparrow.core.components import Camera2D, Transform
from sparrow.core.scene import Scene
from sparrow.graphics.renderer.settings import (
    BlitRendererSettings,
    ResolutionSettings,
    SunlightSettings,
)


class SpashScreenScene(Scene):
    def __init__(self, app: Application):
        self.w, self.h = 1920, 1080

        self.settings = BlitRendererSettings(
            ResolutionSettings(
                logical_width=self.w,
                logical_height=self.h,
            ),
            SunlightSettings(),
        )

        super().__init__(app, self.settings)

    def on_start(self):
        self.world.create_entity(Transform(), Camera2D())

        create_player(self.world, sx=3, sy=3)

        super().on_start()

    def on_update(self):
        super().on_update()

        if self.frame_index > 120:
            self.app.change_scene(PolygonScene)

    def get_render_frame(self):
        return super().get_render_frame()
