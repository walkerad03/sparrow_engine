from __future__ import annotations

from dataclasses import dataclass

import moderngl

from sparrow.graphics.ecs.frame_submit import RenderFrameInput
from sparrow.graphics.renderer.renderer import Renderer
from sparrow.graphics.renderer.settings import RendererSettings


@dataclass(frozen=True, slots=True)
class RenderViewport:
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class RenderContext:
    gl: moderngl.Context


@dataclass(frozen=True, slots=True)
class RendererSettingsResource:
    settings: RendererSettings


@dataclass(frozen=True, slots=True)
class RendererResource:
    renderer: Renderer


@dataclass(frozen=True, slots=True)
class RenderFrame:
    frame: RenderFrameInput
