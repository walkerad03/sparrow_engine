import pytest
from PIL import Image

from sparrow.assets.importers.mesh import ObjImporter
from sparrow.assets.importers.shader import ShaderImporter
from sparrow.assets.importers.texture import TextureImporter
from sparrow.assets.types import MeshData, ShaderSource, TextureData


def test_obj_importer_simple_triangle(tmp_path):
    # Create a valid minimal OBJ file
    obj_content = """
    v 0.0 0.0 0.0
    v 1.0 0.0 0.0
    v 0.0 1.0 0.0
    vn 0.0 0.0 1.0
    vt 0.0 0.0
    f 1/1/1 2/1/1 3/1/1
    """
    f = tmp_path / "triangle.obj"
    f.write_text(obj_content)

    importer = ObjImporter()
    mesh_data = importer.import_file(f)

    assert isinstance(mesh_data, MeshData)
    # 3 vertices * (3 pos + 3 norm + 2 uv) * 4 bytes/float = 3 * 8 * 4 = 96 bytes
    assert len(mesh_data.vertices) == 96
    assert mesh_data.vertex_layout.stride_bytes == 32


def test_obj_importer_invalid_file(tmp_path):
    f = tmp_path / "empty.obj"
    f.write_text("")

    importer = ObjImporter()
    with pytest.raises(ValueError, match="No geometry found"):
        importer.import_file(f)


def test_texture_importer_png(tmp_path):
    # Create a simple red 2x2 PNG
    img = Image.new("RGB", (2, 2), color="red")
    f = tmp_path / "test.png"
    img.save(f)

    importer = TextureImporter()
    tex_data = importer.import_file(f)

    assert isinstance(tex_data, TextureData)
    assert tex_data.width == 2
    assert tex_data.height == 2
    assert tex_data.components == 4  # Should always convert to RGBA
    assert len(tex_data.data) == 2 * 2 * 4  # 16 bytes


def test_shader_importer(tmp_path):
    code = "#version 330 core\nvoid main() {}"
    f = tmp_path / "test.glsl"
    f.write_text(code)

    importer = ShaderImporter()
    shader_source = importer.import_file(f)

    assert isinstance(shader_source, ShaderSource)
    assert shader_source.source == code
    assert shader_source.path == str(f)
