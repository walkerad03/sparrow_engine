from game.create_entities import create_entities_system
from game.freecam import freecam_system
from sparrow.core import Scene, Stage
from sparrow.ecs import World


class GameScene(Scene):
    def __init__(self):
        super().__init__(id="game_scene")

        self.scheduler.add_system(Stage.SETUP, create_entities_system)
        self.scheduler.add_system(Stage.FIXED_UPDATE, freecam_system)

    def setup(self, world: World) -> None:
        super().setup(world)

    def update_fixed(self, world: World) -> None:
        super().update_fixed(world)

    def update_variable(self, world: World, alpha: float) -> None:
        super().update_variable(world, alpha)

    def teardown(self, world: World) -> None:
        super().teardown(world)
