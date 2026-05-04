# sparrow/core/scene.py
from sparrow.core.scheduler import Scheduler, Stage
from sparrow.ecs import World
from sparrow.graphics.integration import extract_render_frame_system
from sparrow.systems.camera import camera_prepare_system
from sparrow.systems.graphics import graphics_system
from sparrow.systems.input import input_system
from sparrow.systems.network import (
    network_pump_system,
    network_sync_out_system,
    process_network_events_system,
)
from sparrow.systems.physics import (
    physics_init_system,
    physics_step_system,
    physics_sync_system,
)
from sparrow.systems.sim_time import simulation_time_system
from sparrow.systems.spatial_indexing import spatial_indexing_system
from sparrow.systems.translation import translation_system
from sparrow.types import SystemId


class Scene:
    def __init__(self, id: str):
        self.id = id
        self.scheduler = Scheduler()

        self._register_default_systems()

    def _register_default_systems(self):
        self.scheduler.add_system(
            Stage.FIXED_UPDATE,
            input_system,
            name=SystemId("input"),
        )
        self.scheduler.add_system(
            Stage.FIXED_UPDATE,
            network_pump_system,
            name=SystemId("network_pump"),
            after=SystemId("input"),
            before=SystemId("process_network_events"),
        )
        self.scheduler.add_system(
            Stage.FIXED_UPDATE,
            process_network_events_system,
            name=SystemId("process_network_events_system"),
            after=SystemId("network_pump"),
            before=SystemId("simulation_time"),
        )
        self.scheduler.add_system(
            Stage.FIXED_UPDATE,
            simulation_time_system,
            name=SystemId("simulation_time"),
        )

        self.scheduler.add_system(
            Stage.FIXED_UPDATE,
            physics_init_system,
            name=SystemId("physics_init"),
        )
        self.scheduler.add_system(
            Stage.FIXED_UPDATE,
            physics_step_system,
            name=SystemId("physics_step"),
            after=SystemId("physics_init"),
        )
        self.scheduler.add_system(
            Stage.FIXED_UPDATE,
            physics_sync_system,
            name=SystemId("physics_sync"),
            after=SystemId("physics_step"),
        )
        self.scheduler.add_system(
            Stage.FIXED_UPDATE,
            translation_system,
            name=SystemId("translation"),
            after=SystemId("physics_sync"),
        )
        self.scheduler.add_system(
            Stage.FIXED_UPDATE,
            spatial_indexing_system,
            name=SystemId("spatial_indexing"),
            after=SystemId("translation"),
        )
        self.scheduler.add_system(
            Stage.FIXED_UPDATE,
            network_sync_out_system,
            after=SystemId("spatial_indexing"),
        )

        self.scheduler.add_system(
            Stage.VARIABLE_UPDATE,
            camera_prepare_system,
            name=SystemId("prepare_camera"),
        )
        self.scheduler.add_system(
            Stage.VARIABLE_UPDATE,
            extract_render_frame_system,
            name=SystemId("extract_frame"),
            after=SystemId("prepare_camera"),
        )
        self.scheduler.add_system(
            Stage.VARIABLE_UPDATE,
            graphics_system,
            after=SystemId("extract_frame"),
        )

    def setup(self, world: World) -> None:
        self.scheduler.run_stage(Stage.SETUP, world)

    def update_fixed(self, world: World) -> None:
        self.scheduler.run_stage(Stage.FIXED_UPDATE, world)

    def update_variable(self, world: World, alpha: float) -> None:
        self.scheduler.run_stage(Stage.VARIABLE_UPDATE, world)

    def teardown(self, world: World) -> None:
        self.scheduler.run_stage(Stage.TEARDOWN, world)
