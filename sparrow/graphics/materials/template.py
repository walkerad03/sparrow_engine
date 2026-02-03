from dataclasses import dataclass, field
from typing import Any, Dict

from sparrow.assets import AssetHandle, ShaderSource


@dataclass
class MaterialTemplate:
    """
    Defines a class of materials (e.g., "StandardPBR", "Toon", "Water").
    It links to the shader source code and defines default uniform values.
    """

    name: str
    vertex_shader: AssetHandle[ShaderSource]
    fragment_shader: AssetHandle[ShaderSource]
    # TODO: Add .geom and .comp back in

    # Default values for uniforms if an instance doesn't provide them
    defaults: Dict[str, Any] = field(default_factory=dict)
    # Defines to inject into the shader (e.g., {"USE_NORMAL_MAP": "1"})
    defines: Dict[str, str] = field(default_factory=dict)

    depth_test: bool = True
    cull_face: bool = True
    blend: bool = False

    def __hash__(self):
        """Return hash based on shader IDs to help with sorting/batching."""
        return hash(
            (
                self.vertex_shader.id,
                self.fragment_shader.id,
                tuple(self.defines.items()),
            )
        )
