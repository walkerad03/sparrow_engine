# main.py
import logging

from game import BlackHoleScene, GameScene
from sparrow.debug import setup_logging
from sparrow.runtime import Application, ApplicationConfig

setup_logging()
logger = logging.getLogger("sparrow.main")


def main():
    """Main entry point to initialize and run the Sparrow engine."""

    config = ApplicationConfig(
        target_ups=60,
        entity_cap=10_000,
        show_cursor=False,
    )
    app = Application(config)
    scene = BlackHoleScene()

    app.load_scene(scene)
    app.run()


if __name__ == "__main__":
    main()
