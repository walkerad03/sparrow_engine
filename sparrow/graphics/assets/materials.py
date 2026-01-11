from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal

MaterialDomain = Literal["sprite", "mesh"]
RenderPassTag = Literal["gbuffer", "forward"]


@dataclass(frozen=True)
class Material:
    name: str
    shader: str
    domain: MaterialDomain
    pass_tag: RenderPassTag
    depth_test: bool = True
    blend: Literal["opaque", "alpha", "add"] = "opaque"


@dataclass(frozen=True)
class MaterialInstance:
    material: str
    uniforms: Dict[str, float | tuple[float]] | None = None
    textures: Dict[str, str] | None = None


class MaterialLibrary:
    def __init__(self):
        self._materials: Dict[str, Material] = {}

    def register(self, material: Material) -> None:
        self._materials[material.name] = material

    def get(self, name: str) -> Material:
        return self._materials[name]
