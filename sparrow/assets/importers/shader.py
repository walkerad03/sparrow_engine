# sparrow/assets/importers/shader.py
from pathlib import Path

from sparrow.assets.importers.base import AssetImporter
from sparrow.assets.types import ShaderSource


class ShaderImporter(AssetImporter):
    def import_file(self, path: Path) -> ShaderSource:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        return ShaderSource(source=source, path=str(path))
