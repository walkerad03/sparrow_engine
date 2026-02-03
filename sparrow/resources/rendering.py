from __future__ import annotations

from dataclasses import dataclass

import moderngl

from sparrow.graphics.core.renderer import Renderer
from sparrow.graphics.core.settings import RendererSettings
from sparrow.graphics.integration.frame import RenderFrame


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
class RenderFrameResource:
    frame: RenderFrame
