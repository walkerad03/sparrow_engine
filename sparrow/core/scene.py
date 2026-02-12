# sparrow/core/scene.py
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import pygame

from sparrow.core.scheduler import Scheduler, Stage
from sparrow.core.world import World
from sparrow.graphics.core.settings import RendererSettings
from sparrow.graphics.integration.extraction import extract_render_frame_system
from sparrow.input.context import InputContext
from sparrow.input.handler import InputHandler
from sparrow.systems.lifetime import lifetime_system
from sparrow.systems.movement import movement_system
from sparrow.systems.physics import physics_system
from sparrow.systems.rendering import render_system
from sparrow.systems.sim_time import simulation_time_system
from sparrow.types import SystemId

if TYPE_CHECKING:
    from sparrow.core.application import Application


class SystemNames:
    CAMERA = SystemId("camera")
    PHYSICS = SystemId("physics")
    LIFETIME = SystemId("lifetime")
    MOVEMENT = SystemId("movement")
    SIMULATION_TIME = SystemId("simulation_time")


class Scene:
    render_enabled: bool = True

    def __init__(
        self,
        app: Application,
        renderer_settings: Optional[RendererSettings] = None,
    ):
        self.world = World()
        self.app = app
        self.scheduler = Scheduler()

        self._pending_renderer_settings = renderer_settings

        self._register_default_systems()
        self._setup_input()

        if renderer_settings:
            self.world.resource_add(renderer_settings)
        else:
            self.world.resource_add(RendererSettings())

    def _setup_input(self):
        input_handler = InputHandler()
        self.world.resource_add(input_handler)

        base_ctx = InputContext("default")
        base_ctx.bind(pygame.K_w, "UP")
        base_ctx.bind(pygame.K_s, "DOWN")
        base_ctx.bind(pygame.K_a, "LEFT")
        base_ctx.bind(pygame.K_d, "RIGHT")
        base_ctx.bind(pygame.K_SPACE, "SPACE")

        input_handler.push_context(base_ctx)

    def _register_default_systems(self):
        self.scheduler.add_system(
            Stage.STARTUP,
            simulation_time_system,
            name=SystemNames.SIMULATION_TIME,
        )
        self.scheduler.add_system(
            Stage.PHYSICS, physics_system, name=SystemNames.PHYSICS
        )
        self.scheduler.add_system(
            Stage.POST_UPDATE, lifetime_system, name=SystemNames.LIFETIME
        )
        self.scheduler.add_system(
            Stage.UPDATE, movement_system, name=SystemNames.MOVEMENT
        )

    def on_start(self) -> None:
        """Called when the scene is first activated."""
        self.scheduler.run_stage(Stage.STARTUP, self.world)

    def on_update(self) -> None:
        """Called every frame to update game logic."""
        self.scheduler.run_stage(Stage.INPUT, self.world)
        self.scheduler.run_stage(Stage.UPDATE, self.world)
        self.scheduler.run_stage(Stage.PHYSICS, self.world)
        self.scheduler.run_stage(Stage.POST_UPDATE, self.world)

        # TODO: Poll input, window events, resize handling.
        # If resized, update renderer settings and rebuild graph or trigger resize path.

    def on_render(self) -> None:
        """Called every frame to submit render data (if rendering is enabled)."""
        if not self.render_enabled:
            return

        extract_render_frame_system(self.world)
        render_system(self.world)

    def on_exit(self) -> None:
        """Called when transitioning away from this scene."""
        pass
