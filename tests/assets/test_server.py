import pytest

from sparrow.assets.handle import AssetHandle
from sparrow.assets.server import AssetServer


def test_asset_server_async_load(tmp_path):
    f = tmp_path / "test_async.glsl"
    f.write_text("void main() {}")

    server = AssetServer(asset_root=tmp_path)

    handle = server.load("test_async.glsl")

    assert isinstance(handle, AssetHandle)
    assert handle.path == "test_async.glsl"

    assert handle.id not in server.registry

    server._executor.shutdown(wait=True)

    loaded_ids = server.update()

    assert handle.id in loaded_ids
    assert handle.id in server.registry

    loaded_data = server.registry.get(handle.id)
    assert loaded_data.source == "void main() {}"


def test_asset_server_caching(tmp_path):
    f = tmp_path / "cached_file.glsl"
    f.write_text("void main() {}")

    server = AssetServer(asset_root=tmp_path)

    h1 = server.load("cached_file.glsl")
    h2 = server.load("cached_file.glsl")

    assert h1 == h2
    assert h1.id == h2.id
