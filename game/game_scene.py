from game.asteroid_orbit import asteroid_orbit_system
from game.create_entities import create_entities_system
from game.freecam import freecam_system
from game.gravity import gravity_system
from game.ring_pipeline import build_ring_pipeline
from sparrow.core import Scene, Stage
from sparrow.ecs import World
from sparrow.graphics.core.renderer import Renderer
from sparrow.types import SystemId


class GameScene(Scene):
    def __init__(self):
        super().__init__(id="game_scene")

        self.scheduler.add_system(Stage.SETUP, create_entities_system)
        self.scheduler.add_system(
            Stage.FIXED_UPDATE,
            asteroid_orbit_system,
            name=SystemId("asteroid_orbit"),
            before=SystemId("translation"),
        )
        self.scheduler.add_system(
            Stage.FIXED_UPDATE,
            gravity_system,
            name=SystemId("gravity"),
            before=SystemId("translation"),
        )
        self.scheduler.add_system(Stage.FIXED_UPDATE, freecam_system)

    def setup(self, world: World) -> None:
        renderer = world.res_get(Renderer)
        if renderer:
            renderer.set_pipeline(build_ring_pipeline)

        super().setup(world)

    def update_fixed(self, world: World) -> None:
        super().update_fixed(world)

    def update_variable(self, world: World, alpha: float) -> None:
        super().update_variable(world, alpha)

    def teardown(self, world: World) -> None:
        super().teardown(world)
