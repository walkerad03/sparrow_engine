# sparrow/assets/server.py
import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Queue
from typing import Dict, List

from sparrow.assets.handle import AssetHandle, AssetId
from sparrow.assets.importers.base import AssetImporter
from sparrow.assets.importers.mesh import ObjImporter
from sparrow.assets.importers.shader import ShaderImporter
from sparrow.assets.importers.texture import TextureImporter
from sparrow.assets.registry import AssetRegistry


class AssetServer:
    def __init__(self, asset_root: Path) -> None:
        self.root = asset_root
        self.registry = AssetRegistry()

        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="AssetWorker"
        )
        self._loaded_queue = Queue()

        self._handles: Dict[str, AssetHandle] = {}  # Path -> Handle

        self._importers: Dict[str, AssetImporter] = {
            ".obj": ObjImporter(),
            ".png": TextureImporter(),
            ".jpg": TextureImporter(),
            ".glsl": ShaderImporter(),
            ".frag": ShaderImporter(),
            ".vert": ShaderImporter(),
            ".comp": ShaderImporter(),
        }

    def load(self, path: str) -> AssetHandle:
        """
        Non-blocking load request. Return handle instantly.
        """
        if path in self._handles:
            return self._handles[path]

        asset_id = AssetId(
            int(hashlib.sha256(path.encode()).hexdigest(), 16) % (10**16)
        )
        handle = AssetHandle(asset_id, path)
        self._handles[path] = handle

        full_path = self.root / path
        self._executor.submit(self._worker_load, asset_id, full_path)

        return handle

    def _worker_load(self, asset_id: AssetId, full_path: Path) -> None:
        """
        Load asset on background thread.
        """
        try:
            ext = full_path.suffix.lower()
            importer = self._importers.get(ext)
            if not importer:
                raise ValueError(f"No importer for {ext}")

            data = importer.import_file(full_path)
            self._loaded_queue.put((asset_id, data))
        except Exception as e:
            print(f"Failed to load {full_path}: {e}")

    def update(self) -> List[AssetId]:
        """
        Called on the Main Thread every frame.
        Return list of newly loaded AssetIds (so Renderer can upload them).
        """
        loaded_ids = []
        while not self._loaded_queue.empty():
            asset_id, data = self._loaded_queue.get()
            self.registry.store(asset_id, data)
            loaded_ids.append(asset_id)

        return loaded_ids
