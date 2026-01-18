from dataclasses import dataclass
from typing import Optional

from sparrow.graphics.ecs.frame_submit import CameraData


@dataclass(frozen=True)
class CameraOutput:
    active: Optional[CameraData] = None
