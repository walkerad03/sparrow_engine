from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol

import moderngl

from sparrow.core.world import World
from sparrow.graphics.assets.materials import MaterialLibrary
from sparrow.graphics.assets.meshes import MeshLibrary
from sparrow.graphics.assets.shaders import ShaderLibrary
from sparrow.graphics.camera import Camera3D
from sparrow.graphics.renderer.draw_list import RenderDrawList
from sparrow.graphics.renderer.frame import FrameResources


@dataclass
class RenderContext:
    ctx: moderngl.Context
    camera: Camera3D
    shaders: ShaderLibrary
    materials: MaterialLibrary
    meshes: MeshLibrary
    frame: FrameResources
    draw_list: RenderDrawList


class RenderPass(Protocol):
    name: str

    def execute(self, rc: RenderContext) -> None: ...


class RenderGraph:
    def __init__(self) -> None:
        self._passes: List[RenderPass] = []

    def add_pass(self, p: RenderPass) -> None:
        self._passes.append(p)

    def execute(self, rc: RenderContext) -> None:
        for p in self._passes:
            p.execute(rc)
