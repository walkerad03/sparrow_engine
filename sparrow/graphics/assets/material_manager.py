# sparrow/graphics/assets/material_manager.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sparrow.graphics.util.ids import MaterialId, TextureId


@dataclass(slots=True)
class Material:
    """
    Minimal deferred material.

    For a starter deferred pipeline:
        - base_color texture and factor
        - normal map (optional)
        - roughness/metalness (packed or scalar)

    NOTE: occlusion, roughness, and metalness are all scalar values
    """

    base_color_tex: Optional[TextureId] = None
    normal_tex: Optional[TextureId] = None
    orm_tex: Optional[TextureId] = None  # occlusion/roughness/metalness packed rgb
    base_color_factor: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    roughness: float = 1.0
    metalness: float = 0.0


class MaterialManager:
    """Stores materials and provides binding plans for passes."""

    def __init__(self) -> None: ...

    def create(self, material_id: MaterialId, material: Material) -> None:
        """Register or replace a material."""
        ...

    def get(self, material_id: MaterialId) -> Material:
        """Get a material by id."""
        raise NotImplementedError
