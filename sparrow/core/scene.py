# sparrow/core/scene.py
from sparrow.core.scheduler import Scheduler, Stage
from sparrow.ecs import World
from sparrow.systems.sim_time import simulation_time_system
from sparrow.systems.translation import translation_system


class Scene:
    def __init__(self, id: str):
        self.id = id
        self.scheduler = Scheduler()

        self._register_default_systems()

    def _register_default_systems(self):
        self.scheduler.add_system(Stage.FIXED_UPDATE, simulation_time_system)
        self.scheduler.add_system(Stage.FIXED_UPDATE, translation_system)

    def setup(self, world: World) -> None:
        self.scheduler.run_stage(Stage.SETUP, world)

    def update_fixed(self, world: World) -> None:
        self.scheduler.run_stage(Stage.FIXED_UPDATE, world)

    def update_variable(self, world: World, alpha: float) -> None:
        self.scheduler.run_stage(Stage.VARIABLE_UPDATE, world)

    def teardown(self, world: World) -> None:
        self.scheduler.run_stage(Stage.TEARDOWN, world)
