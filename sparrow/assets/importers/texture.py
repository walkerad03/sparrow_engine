# sparrow/assets/importers/texture.py
from pathlib import Path

from PIL import Image

from sparrow.assets.importers.base import AssetImporter
from sparrow.assets.types import TextureData


class TextureImporter(AssetImporter):
    def import_file(self, path: Path) -> TextureData:
        with Image.open(path) as img:
            converted = img.convert("RGBA")

            # NOTE: if OpenGL coordinate mismatch occurs
            # converted = converted.transpose(Image.FLIP_TOP_BOTTOM)

            width, height = converted.size
            data = converted.tobytes()

        return TextureData(data=data, width=width, height=height, components=4)
