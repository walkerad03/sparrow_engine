# sparrow/graphics/integration/components.py
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from sparrow.assets.handle import AssetHandle
from sparrow.assets.types import MeshData, TextureData
from sparrow.types import Color3, Color4, Scalar


@dataclass(frozen=True)
class Mesh:
    """
    Component: Links an entity to a 3D model asset.
    """

    __soa_dtype__ = [
        ("handle", "O"),
        ("mesh_id", "i8"),
        ("visible", "?"),
        ("cast_shadows", "?"),
        ("render_layer", "i4"),
    ]
    dtype = np.dtype(__soa_dtype__)

    handle: AssetHandle[MeshData]
    mesh_id: int = -1
    visible: bool = True
    cast_shadows: bool = True
    render_layer: int = 0  # Optional for custom sorting

    def __post_init__(self) -> None:
        if hasattr(self.handle, "id"):
            object.__setattr__(self, "mesh_id", int(self.handle.id))


@dataclass(frozen=True)
class Material:
    """
    Component: Defines surface properties for the renderer.
    This corresponds to a MaterialInstance in the renderer.
    """

    __soa_dtype__ = [
        ("albedo", "O"),
        ("base_color", "4f4"),  # vec4
        ("roughness", "f4"),
        ("metallic", "f4"),
        ("emissive", "f4"),
    ]

    # PLANNED: Convert this to a handle for a MaterialInstance asset
    albedo: Optional[AssetHandle[TextureData]] = None
    base_color: Color4 = (1.0, 1.0, 1.0, 1.0)
    roughness: Scalar = 0.5
    metallic: Scalar = 0.0
    emissive: Scalar = 0.0

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(f"Invalid Material property: {key}")


@dataclass(frozen=True)
class Camera:
    """
    Component: Defines a viewpoint.
    """

    __soa_dtype__ = [
        ("fov", "f4"),
        ("near", "f4"),
        ("far", "f4"),
        ("active", "?"),
    ]

    fov: float = 60.0
    near: float = 0.1
    far: float = 1000.0
    active: bool = True


@dataclass(frozen=True)
class DirectionalLight:
    """
    Component: Global sun-like light.
    """

    __soa_dtype__ = [
        ("color", "3f4"),
        ("intensity", "f4"),
        ("cast_shadows", "?"),
    ]

    color: Color3 = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    cast_shadows: bool = True
