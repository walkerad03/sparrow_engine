# sparrow/runtime/application.py
from dataclasses import dataclass
from typing import Any, List, Optional

from sparrow.ecs.world import World
from sparrow.runtime.managers import InterfaceManager, ResourceManager
from sparrow.runtime.timing import FixedStep


@dataclass
class ApplicationConfig:
    """Configuration settings for the Application Runtime.

    Attributes:
        target_ups (int): The desired frequency for fixed-step updates.
        max_frame_time (float): The maximum allowed time for a single frame.
        capacity (int): The initial entity capacity for the ECS World.
    """

    target_ups: int = 60
    max_frame_time: float = 0.25
    capacity: int = 1_000_000


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

        self.world = World(capacity=self.config.capacity)

        self.interface = InterfaceManager()
        self.resources = ResourceManager(ctx=self.interface.ctx)
        self.clock = FixedStep(
            target_fps=self.config.target_ups,
            max_frame_time=self.config.max_frame_time,
        )

        self.world.res_add(self.interface)
        self.world.res_add(self.resources)

        self.raw_event_buffer: List[Any] = []
        self._active_scene: Optional[Any] = None

    def load_scene(self, scene: Any) -> None:
        """Transitions the application to a new scene.

        Args:
            scene (Any): The scene object containing its own ECS Manager.
        """
        if self._active_scene:
            self._active_scene.teardown()
            self.resources.unload_unused(self._active_scene.id)

        self._active_scene = scene
        self._active_scene.setup(self.world)

    def run(self) -> None:
        """Starts the main game loop.

        This method initializes the clock and continues iterating until `running`
        is set to False. It handles event polling, fixed-step logic updates,
        and variable-rate rendering.
        """
        self.running = True
        self.clock.start()

        while self.running:
            self.raw_event_buffer = self.interface.poll_events()

            steps = self.clock.advance()

            self.interface.clear(color=(0.1, 0.1, 0.1, 1.0))

            if self._active_scene:
                for event in self.raw_event_buffer:
                    self.world.event_add(event)
                self.raw_event_buffer.clear()

                # TODO: Pass clock data into a dedicated time resource
                # TODO: Update world using scheduler instead of scene
                for _ in range(steps):
                    self._active_scene.update_fixed(
                        self.world,
                        self.clock.dt,
                    )

                self._active_scene.update_variable(
                    self.world,
                    self.clock.alpha,
                )

            self.interface.swap_buffers()

            if self.interface.should_close():
                self.running = False

    def quit(self) -> None:
        """Signals the application loop to terminate."""
        self.running = False
