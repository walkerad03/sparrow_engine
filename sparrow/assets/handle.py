# sparrow/assets/handle.py
from dataclasses import dataclass
from typing import Generic, NewType, TypeVar

AssetId = NewType("AssetId", int)  # 64-bit integer GUID
T = TypeVar("T")  # Type of data (MeshData, TextureData)


@dataclass(frozen=True)
class AssetHandle(Generic[T]):
    """
    Lightweight reference to an asset.
    Holding this does not guarantee that the asset is loaded.
    """

    id: AssetId
    path: str
