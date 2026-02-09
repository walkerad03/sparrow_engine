# sparrow/graphics/passes/clear.py
import colorsys
import time
from dataclasses import dataclass
from typing import Optional

from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
)
from sparrow.graphics.utils.ids import ResourceId
from sparrow.types import Color4


def _rainbow_color(t: float, speed: float = 0.5) -> Color4:
    hue = (t * speed) % 1.0
    return (*colorsys.hsv_to_rgb(hue, 1.0, 1.0), 1.0)


@dataclass
class ClearPass(RenderPass):
    """
    Clear the specified target (or screen if target is None).
    """

    color: Color4 = (0.1, 0.1, 0.1, 1.0)
    depth: float = 1.0
    target: Optional[ResourceId] = None

    def build(self) -> PassBuildInfo:
        writes = []
        if self.target:
            writes.append(PassResourceUse(self.target, "write"))

        return PassBuildInfo(pass_id=self.pass_id, reads=[], writes=writes)

    def execute(self, ctx: PassExecutionContext) -> None:
        t = time.time()
        self.color = _rainbow_color(t, speed=1)

        if self.target:
            fbo = ctx.graph_resources[self.target]
            fbo.clear(*self.color, depth=self.depth)
        else:
            ctx.gl.clear(*self.color, depth=self.depth)
