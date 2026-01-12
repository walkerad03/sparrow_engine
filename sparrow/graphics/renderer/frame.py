from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import moderngl

from sparrow.graphics.gbuffer import GBuffer


@dataclass
class FrameResources:
    gbuffer: GBuffer
    scene_fbo: Any

    vox_albedo_occ: moderngl.Texture3D
    vox_normal: moderngl.Texture3D

    # Cached values (not required)
    vox_res: tuple[int, int, int]
