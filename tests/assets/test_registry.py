import pytest

from sparrow.assets.handle import AssetId
from sparrow.assets.registry import AssetRegistry


def test_registry_store_and_get():
    registry = AssetRegistry()
    asset_id = AssetId(123)
    data = {"some": "data"}

    registry.store(asset_id, data)

    assert asset_id in registry
    assert registry.get(asset_id) == data


def test_registry_missing_item():
    registry = AssetRegistry()
    asset_id = AssetId(999)

    assert asset_id not in registry
    assert registry.get(asset_id) is None


def test_registry_clear():
    registry = AssetRegistry()
    registry.store(AssetId(1), "A")
    registry.store(AssetId(2), "B")

    registry.clear()

    assert AssetId(1) not in registry
    assert AssetId(2) not in registry
