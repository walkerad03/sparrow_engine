# sparrow/graphics/shaders/shader_manager.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Sequence, Tuple

import moderngl

from sparrow.graphics.shaders.program_types import ProgramHandle, ShaderStages
from sparrow.graphics.util.ids import ShaderId


def _make_variant_key(
    req: ShaderRequest,
) -> Tuple[ShaderId, Tuple[Tuple[str, str], ...]]:
    defines = tuple(sorted((d.key, d.value) for d in req.defines))
    return (req.shader_id, defines)


def _load_source(src: str) -> str:
    """
    Load shader source.

    If src looks like a file path, load it.
    Otherwise assume it is raw GLSL.
    """
    p = Path(src)
    if p.exists():
        return p.read_text(encoding="utf-8")
    return src


def _inject_defines(source: str, defines: Sequence[ShaderDefine]) -> str:
    if not defines:
        return source

    lines = [f"#define {d.key} {d.value}" for d in defines]
    return "\n".join(lines) + "\n\n" + source


def _load_stage(src: str | None, req: ShaderRequest) -> str | None:
    if src is None:
        return None
    text = _load_source(src)
    return _inject_defines(text, req.defines)


@dataclass(frozen=True, slots=True)
class ShaderDefine:
    """Single preprocessor define used to build program variants."""

    key: str
    value: str = "1"


@dataclass(frozen=True, slots=True)
class ShaderRequest:
    """
    Request to load/compile a shader program.

    `stages` can point to:
      - filesystem paths
      - package resources
      - raw source strings (if your IncludeResolver supports it)
    """

    shader_id: ShaderId
    stages: ShaderStages
    defines: Sequence[ShaderDefine] = ()
    label: str = ""


class ShaderManager:
    """
    Central shader loader/compiler/cache.

    Responsibilities:
      - resolve includes
      - apply defines
      - compile/link (or compile compute)
      - cache program variants
      - optional hot reload support
    """

    def __init__(self, gl: moderngl.Context, *, include_paths: Sequence[str]) -> None:
        self._gl = gl
        self._include_paths = tuple(include_paths)

        self._shader_cache: Dict[
            tuple[ShaderId, tuple[tuple[str, str], ...]], ProgramHandle
        ] = {}
        self._source_mtimes: Dict[str, float] = {}

    def get(self, req: ShaderRequest) -> ProgramHandle:
        """Return a compiled program for the request, compiling and caching as needed."""
        key = _make_variant_key(req)
        cached = self._shader_cache.get(key)
        if cached is not None:
            return cached

        stages = req.stages

        # TODO: Replace individual stages with a tagged union
        # dataclass to remove check below.
        vert = _load_stage(stages.vertex, req)
        frag = _load_stage(stages.fragment, req)
        geom = _load_stage(stages.geometry, req)
        comp = _load_stage(stages.compute, req)

        if comp is not None:
            program = self._gl.compute_shader(comp)
        else:
            if vert is None or frag is None:
                raise ValueError(
                    f"Shader {req.shader_id} is missing vertex or fragment stage."
                )
            program = self._gl.program(
                vertex_shader=vert,
                fragment_shader=frag,
                geometry_shader=geom,
            )

        handle = ProgramHandle(program=program, label=req.label or str(req.shader_id))
        self._shader_cache[key] = handle
        return handle

    def invalidate(self, shader_id: ShaderId) -> None:
        """Drop cached programs for a shader id; next get() recompiles."""
        to_delete = [k for k in self._shader_cache if k[0] == shader_id]
        for k in to_delete:
            prog = self._shader_cache.pop(k)
            try:
                prog.program.release()
            except Exception:
                pass

    def reload_changed(self) -> Sequence[ShaderId]:
        """
        If hot-reload is enabled, recompile programs whose sources changed.

        Returns shader ids that were reloaded successfully.
        """
        return []
