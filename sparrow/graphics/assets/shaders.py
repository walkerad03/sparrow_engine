from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import moderngl


@dataclass
class ShaderProgram:
    program: moderngl.Program


class ShaderLibrary:
    def __init__(self, ctx: moderngl.Context):
        self._ctx = ctx
        self._programs: Dict[str, ShaderProgram] = {}
        self._sources: Dict[str, tuple[Path, Path]] = {}

    def register_engine_shader(self, key: str, vert: Path, frag: Path) -> None:
        self._sources[key] = (vert, frag)

    def register_override(self, key: str, vert: Path, frag: Path) -> None:
        self._sources[key] = (vert, frag)
        if key in self._programs:
            del self._programs[key]  # force recompile

    def get(self, key: str) -> ShaderProgram:
        if key not in self._programs:
            vert, frag = self._sources[key]
            self._programs[key] = ShaderProgram(
                program=self._ctx.program(
                    vertex_shader=vert.read_text(),
                    fragment_shader=frag.read_text(),
                )
            )
        return self._programs[key]
