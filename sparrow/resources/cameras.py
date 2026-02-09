from dataclasses import dataclass
from typing import Optional

from sparrow.graphics.integration.frame import CameraData


@dataclass(frozen=True)
class CameraOutput:
    active: Optional[CameraData] = None
