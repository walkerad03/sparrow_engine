# sparrow/graphics/resources/manager.py
from typing import Any, Dict

import moderngl

from sparrow.assets.handle import AssetId
from sparrow.assets.server import AssetServer
from sparrow.assets.types import MeshData, ShaderSource, TextureData
from sparrow.graphics.resources.buffer import GPUMesh
from sparrow.graphics.resources.texture import GPUTexture


class GPUResourceManager:
    """
    Syncs CPU assets (from AssetServer) to GPU memory.
    """

    def __init__(self, ctx: moderngl.Context, asset_server: AssetServer):
        self.ctx = ctx
        self.asset_server = asset_server

        self._meshes: Dict[AssetId, GPUMesh] = {}
        self._textures: Dict[AssetId, GPUTexture] = {}
        self._shader_sources: Dict[AssetId, str] = {}

    def sync(self) -> None:
        """
        Fetch newly loaded assets from the server and upload to VRAM.
        """
        loaded_ids = self.asset_server.update()

        if not loaded_ids:
            return

        for asset_id in loaded_ids:
            data = self.asset_server.registry.get(asset_id)
            if data:
                self._upload_asset(asset_id, data)

    def _upload_asset(self, asset_id: AssetId, data: Any) -> None:
        if isinstance(data, MeshData):
            if asset_id in self._meshes:
                self._meshes[asset_id].release()
            self._meshes[asset_id] = GPUMesh(self.ctx, data)

        elif isinstance(data, TextureData):
            if asset_id in self._textures:
                self._textures[asset_id].release()
            self._textures[asset_id] = GPUTexture(self.ctx, data)

        elif isinstance(data, ShaderSource):
            self._shader_sources[asset_id] = data.source

    def get_mesh(self, asset_id: AssetId) -> GPUMesh | None:
        return self._meshes.get(asset_id)

    def get_texture(self, asset_id: AssetId) -> GPUTexture | None:
        return self._textures.get(asset_id)

    def get_shader_source(self, asset_id: AssetId) -> str | None:
        return self._shader_sources.get(asset_id)
