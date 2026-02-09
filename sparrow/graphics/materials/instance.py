# sparrow/graphics/materials/instance.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from sparrow.assets.handle import AssetHandle
from sparrow.assets.types import TextureData
from sparrow.graphics.materials.template import MaterialTemplate


@dataclass
class MaterialInstance:
    """A specific occurrence of a material."""

    template: MaterialTemplate

    # Uniform overrides (Float, Vec3, Mat4, etc.)
    uniforms: Dict[str, Any] = field(default_factory=dict)

    # Texture bindings (Name -> Handle)
    textures: Dict[str, AssetHandle[TextureData]] = field(default_factory=dict)

    def set_uniform(self, name: str, value: Any) -> None:
        self.uniforms[name] = value

    def set_texture(self, name: str, texture: AssetHandle[TextureData]) -> None:
        self.textures[name] = texture

    def get_uniform(self, name: str) -> Any:
        return self.uniforms.get(name, self.template.defaults.get(name))
