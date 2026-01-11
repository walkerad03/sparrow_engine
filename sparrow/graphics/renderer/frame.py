from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sparrow.graphics.gbuffer import GBuffer


@dataclass
class FrameResources:
    gbuffer: GBuffer
    scene_fbo: Any
