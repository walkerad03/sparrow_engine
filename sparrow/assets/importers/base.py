# sparrow/assets/importers/base.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class AssetImporter(ABC):
    @abstractmethod
    def import_file(self, path: Path) -> Any:
        """
        Read file from disk and returns CPU-friendly data object.
        Must be thread-safe.
        """
        pass
