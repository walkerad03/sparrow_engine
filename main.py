# main.py
import logging

from game import GameScene
from sparrow.debug import setup_logging
from sparrow.runtime import Application, ApplicationConfig

setup_logging()
logger = logging.getLogger("sparrow.main")

# TODO: Fix memory leak in asset pipeline
def main():
    """Main entry point to initialize and run the Sparrow engine."""

    config = ApplicationConfig(target_ups=120, entity_cap=1_000_000)
    app = Application(config)
    scene = GameScene()

    app.load_scene(scene)
    app.run()


if __name__ == "__main__":
    main()
