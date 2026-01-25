# sparrow/graphics/assets/material_manager.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from sparrow.graphics.util.ids import MaterialId, TextureId


@dataclass(slots=True)
class Material:
    """
    Minimal deferred/forward material.

    For a starter deferred pipeline:
        - base_color texture and factor
        - normal map (optional)
        - roughness/metalness (packed or scalar)

    NOTE: occlusion, roughness, and metalness are all scalar values
    """

    base_color_tex: Optional[TextureId] = None
    normal_tex: Optional[TextureId] = None
    orm_tex: Optional[TextureId] = (
        None  # occlusion/roughness/metalness packed rgb
    )

    base_color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    roughness: float = 0.5
    metallic: float = 0.0


class MaterialManager:
    """Stores materials and provides binding plans for passes."""

    def __init__(self) -> None:
        self._materials: Dict[MaterialId, Material] = {}

        self.create(
            MaterialId("engine.default"),
            Material(base_color=(1.0, 1.0, 1.0, 1.0)),
        )

    def create(self, material_id: MaterialId, material: Material) -> None:
        """Register or replace a material."""
        self._materials[material_id] = material

    def get(self, material_id: MaterialId) -> Material:
        """Get a material by id."""
        try:
            return self._materials[material_id]
        except KeyError:
            raise KeyError(f"Material '{material_id}' not found")
