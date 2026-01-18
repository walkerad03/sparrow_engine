# main.py

from __future__ import annotations

from pathlib import Path

from game.scenes.test_scene import TestScene
from sparrow.core.application import Application
from sparrow.graphics.debug.profiler import profile


@profile(out_dir=Path(".debug"), enabled=True)
def main() -> None:
    """Main entrypoint for the minimal renderer test app."""
    app = Application(width=1920, height=1080)
    app.run(TestScene)


if __name__ == "__main__":
    main()
