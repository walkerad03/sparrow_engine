# sparrow/assets/__init__.py
from sparrow.assets.defaults import (
    DefaultMeshes,
    DefaultShaders,
    DefaultTextures,
)
from sparrow.assets.handle import AssetHandle, AssetId
from sparrow.assets.server import AssetServer
from sparrow.assets.types import (
    MeshData,
    ShaderSource,
    TextureData,
    VertexLayout,
)

__all__ = [
    "AssetServer",
    "AssetHandle",
    "AssetId",
    "MeshData",
    "TextureData",
    "ShaderSource",
    "VertexLayout",
    "DefaultMeshes",
    "DefaultShaders",
    "DefaultTextures",
]
