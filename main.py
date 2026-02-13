# main.py
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from sparrow.debug.profiler import profile
from sparrow.ecs import World
from sparrow.runtime import Application, ApplicationConfig


class SparrowFormatter(logging.Formatter):
    """Custom formatter to handle fixed-width columns and name cropping."""

    def __init__(self, name_width: int = 20):
        super().__init__("%(levelname)-8s %(bracketed_name)s %(message)s")
        self.name_width = name_width

    def format(self, record):
        name = record.name
        max_name_len = self.name_width - 2
        if len(name) > max_name_len:
            display_name = name[: max_name_len - 1] + "…"
        else:
            display_name = name
        record.bracketed_name = f"[{display_name}]".ljust(self.name_width)
        return super().format(record)


def setup_logging():
    debug_dir = Path(".debug")
    debug_dir.mkdir(exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(SparrowFormatter(name_width=20))
    root.addHandler(console_handler)

    file_handler = logging.FileHandler(debug_dir / "engine_raw.log", mode="w")
    raw_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    file_handler.setFormatter(raw_formatter)
    root.addHandler(file_handler)


setup_logging()
logger = logging.getLogger("sparrow.main")


@dataclass
class Transform:
    dtype = np.dtype([("x", "f4"), ("y", "f4")])

    x: float = 0.0
    y: float = 0.0


class MockScene:
    """A shim to simulate a Game Scene."""

    def __init__(self):
        self.id = "test_scene_01"

    def setup(self, world: World) -> None:
        logger.info(f"Setting up scene: {self.id}")

        for i in range(5):
            ent = world.entity_add()
            world.comp_add(ent, Transform(x=i * 10.0, y=0.0))

        logger.info("Created 5 entities with Transform components.")

    def update_fixed(self, world: World, dt: float) -> None:
        view = world.query(Transform)

        if len(view) > 0:
            view.Transform.x += 1.0

            first_x = view.Transform.x[0]
            logger.info(f"Fixed Update: Entity 0 X-Pos is {first_x:.2f}")

    def update_variable(self, world: World, alpha: float) -> None:
        pass

    def teardown(self) -> None:
        logger.info(f"Tearing down scene: {self.id}")


@profile(enabled=True, out_dir=Path(".debug"))
def main():
    """Main entry point to initialize and run the Sparrow engine."""

    config = ApplicationConfig(target_ups=500, capacity=1000)
    app = Application(config)

    scene = MockScene()
    app.load_scene(scene)

    logger.info("Starting engine main loop...")

    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("External interrupt received. Shutting down.")
    finally:
        app.quit()
        logger.info("Engine shutdown complete.")


if __name__ == "__main__":
    main()
