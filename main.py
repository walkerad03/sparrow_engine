# main.py
from __future__ import annotations

from pathlib import Path

from game.scenes.polygon_scene import PolygonScene
from sparrow.core.application import Application
from sparrow.debug.profiler import profile


@profile(out_dir=Path(".debug"), enabled=False)
def main() -> None:
    """Main entrypoint for the minimal renderer test app."""
    app = Application(width=1920, height=1080)
    app.run(PolygonScene)


if __name__ == "__main__":
    main()
