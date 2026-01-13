# sparrow/graphics/shaders/program_types.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import moderngl


@dataclass(frozen=True, slots=True)
class ShaderStages:
    """
    All stages for a single GPU program.

    Any field may be None if not used (e.g., compute-only uses compute).
    """

    vertex: Optional[str] = None
    fragment: Optional[str] = None
    geometry: Optional[str] = None
    compute: Optional[str] = None
    tess_control: Optional[str] = None
    tess_eval: Optional[str] = None


@dataclass(frozen=True)
class ProgramHandle:
    """
    Wraps a compiled ModernGL program/compute shader.

    Rationale:
      - stable API for passes
      - centralized reload/invalidations
    """

    program: moderngl.Program | moderngl.ComputeShader
    label: str
