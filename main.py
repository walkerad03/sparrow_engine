# main.py
import logging
from pathlib import Path

from game import PhysicsTestScene
from sparrow.debug import setup_logging
from sparrow.debug.line import line_profile
from sparrow.graphics.integration.extraction import extract_render_frame_system
from sparrow.runtime import Application, ApplicationConfig

setup_logging()
logger = logging.getLogger("sparrow.main")


@line_profile(
    out_dir=Path(".debug/profiles"),
    enabled=False,
    target=extract_render_frame_system,
)
def main():
    """Main entry point to initialize and run the Sparrow engine."""

    config = ApplicationConfig(
        target_ups=60,
        entity_cap=100_000,
        show_cursor=False,
    )
    app = Application(config)
    scene = PhysicsTestScene()

    app.load_scene(scene)
    app.run()


if __name__ == "__main__":
    main()
