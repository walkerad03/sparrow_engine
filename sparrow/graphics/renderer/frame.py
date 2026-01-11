from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FrameResources:
    gbuffer: Any
    scene_fbo: Any
