# sparrow/runtime/application.py
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

from sparrow.assets.server import AssetServer
from sparrow.core import Scene
from sparrow.debug.profiler import profile
from sparrow.ecs.world import World
from sparrow.graphics.core.renderer import Renderer
from sparrow.graphics.pipelines import build_standard_3d_pipeline
from sparrow.physics.server import PhysicsServer
from sparrow.runtime.managers import InterfaceManager, ResourceManager
from sparrow.runtime.timing import FixedStep

logger = logging.getLogger("sparrow.runtime")


@dataclass
class ApplicationConfig:
    """Configuration settings for the Application Runtime.

    Attributes:
        target_ups (int): The desired frequency for fixed-step updates.
        max_frame_time (float): The maximum allowed time for a single frame.
        capacity (int): The initial entity capacity for the ECS World.
    """

    target_ups: int = 60
    target_fps: int = 60
    max_frame_time: float = 0.25
    entity_cap: int = 1_000_000
    show_cursor: bool = True


class Application:
    """Drives the core game loop and manages scene execution and runtime modules.

    The Application class acts as the orchestrator for the Sparrow engine, managing
    the lifecycle of runtime-scoped modules like the Interface Manager and
    Resource Manager while driving the main execution loop.

    Attributes:
        config (ApplicationConfig): The configuration used for the runtime.
        running (bool): Whether the application loop is currently executing.
        interface (Optional[Any]): The Interface Manager handling windowing and context.
        resources (Optional[Any]): The Global Resource Manager.
        clock (Optional[Any]): The FixedStep timing helper.
        raw_event_buffer (List[Any]): A list of hardware events collected by the
            interface to be passed to the active scene.
    """

    def __init__(self, config: Optional[ApplicationConfig] = None):
        """Initializes the Application with runtime-scoped modules.

        Args:
            config (Optional[ApplicationConfig]): Custom configuration. Defaults to
                standard 60fps settings.
        """
        self.config = config or ApplicationConfig()
        self.running: bool = False

        self.world = World(capacity=self.config.entity_cap)

        self.interface = InterfaceManager(show_cursor=self.config.show_cursor)
        self.resources = ResourceManager(ctx=self.interface.ctx)
        self.clock = FixedStep(
            timer=self.interface.timer,
            target_ups=self.config.target_ups,
            target_fps=self.config.target_fps,
            max_frame_time=self.config.max_frame_time,
        )
        self.physics = PhysicsServer()

        self.world.res_add(self.interface)
        self.world.res_add(self.resources)
        self.world.res_add(self.clock)
        self.world.res_add(self.physics)

        # TODO: Move this into a system so that we can avoid unnecessary imports
        asset_root = Path(".") / "sparrow" / "assets"
        self.asset_server = AssetServer(asset_root)
        self.world.res_add(self.asset_server)
        self.renderer = Renderer(self.interface.ctx, self.asset_server)
        self.renderer.set_pipeline(build_standard_3d_pipeline)
        self.world.res_add(self.renderer)

        self.raw_event_buffer: List[Any] = []
        self._active_scene: Optional[Scene] = None

    def load_scene(self, scene: Any) -> None:
        """Transitions the application to a new scene.

        Args:
            scene (Any): The scene object containing its own ECS Manager.
        """
        if self._active_scene:
            self._active_scene.teardown(self.world)
            self.resources.unload_unused(self._active_scene.id)

        self._active_scene = scene
        self._active_scene.setup(self.world)

    @profile(enabled=True, out_dir=Path(".debug"))
    def run(self) -> None:
        """Starts the main game loop.

        This method initializes the clock and continues iterating until `running`
        is set to False. It handles event polling, fixed-step logic updates,
        and variable-rate rendering.
        """
        self.running = True
        self.clock.start()

        logger.info("Starting engine main loop...")

        try:
            while self.running:
                self.raw_event_buffer = self.interface.poll_events()

                steps = self.clock.advance()

                if self._active_scene:
                    for event in self.raw_event_buffer:
                        self.world.event_add(event)
                    self.raw_event_buffer.clear()

                    for _ in range(steps):
                        self._active_scene.update_fixed(self.world)

                    self._active_scene.update_variable(
                        self.world, self.clock.alpha
                    )

                    self.interface.swap_buffers()

                    self.clock.sync()

                if self.interface.should_close():
                    self.running = False
        except KeyboardInterrupt:
            logger.info(
                "External interrupt received. Shutting down application loop."
            )
        finally:
            self.quit()
            logger.info("Engine shutdown complete.")

    def quit(self) -> None:
        """Signals the application loop to terminate."""
        self.running = False

        self.physics.shutdown()
