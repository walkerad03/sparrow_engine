# sparrow/core/scene.py
from sparrow.core.scheduler import Scheduler, Stage
from sparrow.ecs import World
from sparrow.graphics.integration import extract_render_frame_system
from sparrow.systems.graphics import graphics_system
from sparrow.systems.input import input_system
from sparrow.systems.sim_time import simulation_time_system
from sparrow.systems.translation import translation_system
from sparrow.types import SystemId


class Scene:
    def __init__(self, id: str):
        self.id = id
        self.scheduler = Scheduler()

        self._register_default_systems()

    def _register_default_systems(self):
        self.scheduler.add_system(Stage.FIXED_UPDATE, simulation_time_system)
        self.scheduler.add_system(Stage.FIXED_UPDATE, translation_system)
        self.scheduler.add_system(
            Stage.VARIABLE_UPDATE,
            extract_render_frame_system,
            name=SystemId("extract_frame"),
        )
        self.scheduler.add_system(
            Stage.VARIABLE_UPDATE,
            graphics_system,
            after=SystemId("extract_frame"),
        )
        self.scheduler.add_system(Stage.FIXED_UPDATE, input_system)

    def setup(self, world: World) -> None:
        self.scheduler.run_stage(Stage.SETUP, world)

    def update_fixed(self, world: World) -> None:
        self.scheduler.run_stage(Stage.FIXED_UPDATE, world)

    def update_variable(self, world: World, alpha: float) -> None:
        self.scheduler.run_stage(Stage.VARIABLE_UPDATE, world)

    def teardown(self, world: World) -> None:
        self.scheduler.run_stage(Stage.TEARDOWN, world)
