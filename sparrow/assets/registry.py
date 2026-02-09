# sparrow/assets/registry.py
from typing import Any, Dict, Optional

from sparrow.assets.handle import AssetId


class AssetRegistry:
    """
    Stores loaded asset data (CPU side) mapped by AssetId.
    """

    def __init__(self) -> None:
        self._storage: Dict[AssetId, Any] = {}

    def store(self, asset_id: AssetId, data: Any) -> None:
        """Register a loaded asset."""
        self._storage[asset_id] = data

    def get(self, asset_id: AssetId) -> Optional[Any]:
        """Retrieve asset data if available."""
        return self._storage.get(asset_id)

    def __contains__(self, asset_id: AssetId) -> bool:
        return asset_id in self._storage

    def clear(self) -> None:
        """Clear all loaded assets (use with caution)."""
        self._storage.clear()
