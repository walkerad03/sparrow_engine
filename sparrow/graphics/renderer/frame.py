from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FrameResources:
    gbuffer: Any
    scene_fbo: Any
    bloom_fbo_1: Any
    bloom_fbo_2: Any
