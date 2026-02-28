from game.black_hole_pipeline import build_black_hole_pipeline
from game.black_hole_setup import create_black_hole_scene_system
from game.freecam import freecam_system
from sparrow.core import Scene, Stage
from sparrow.ecs import World
from sparrow.graphics.core.renderer import Renderer


class BlackHoleScene(Scene):
    def __init__(self):
        super().__init__(id="black_hole_scene")

        self.scheduler.add_system(Stage.SETUP, create_black_hole_scene_system)
        self.scheduler.add_system(Stage.FIXED_UPDATE, freecam_system)

    def setup(self, world: World) -> None:
        super().setup(world)

        renderer = world.res_get(Renderer)
        if renderer:
            renderer.set_pipeline(build_black_hole_pipeline)

    def update_fixed(self, world: World) -> None:
        super().update_fixed(world)

    def update_variable(self, world: World, alpha: float) -> None:
        super().update_variable(world, alpha)

    def teardown(self, world: World) -> None:
        super().teardown(world)
