# sparrow/graphics/graph/pass_base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Literal, Mapping

import moderngl

from sparrow.graphics.integration import RenderFrame
from sparrow.graphics.resources.manager import GPUResourceManager
from sparrow.graphics.resources.shader import ShaderManager
from sparrow.graphics.utils.ids import PassId, ResourceId


@dataclass(frozen=True, slots=True)
class RenderServices:
    """
    Services exposed to every RenderPass during compilation/execution.
    """

    shader_manager: ShaderManager
    gpu_resources: GPUResourceManager

    extras: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PassExecutionContext:
    """
    Context provided to a pass during the execute() phase.

    Passes should treat this as read-only for the duration of `execute()`.

    Attributes:
        gl: Active ModernGL context.
        frame: Per-frame scene submission data (camera, draws, lights, debug flags).
        graph_resources: Graph-owned GPU resources keyed by ResourceId.
            Mapping ResourceId -> moderngl.Texture | moderngl.Buffer
        resolution: Current framebuffer width and height

    Notes:
        Most passes should render to graph-owned textures sized at the renderer's
        internal resolution and only the final present pass should care about the
        window viewport. If you later add logical vs window resolution, this
        context should be extended to include logical_width/logical_height and a
        present viewport rectangle.
    """

    gl: moderngl.Context
    frame: RenderFrame
    graph_resources: Mapping[ResourceId, Any]
    gpu_resources: Any  # For GPUResourceManager
    resolution: tuple[int, int]


@dataclass(frozen=True, slots=True)
class PassResourceUse:
    """Declares how a pass uses a specific resource."""

    id: ResourceId
    role: Literal["read", "write"]
    bind_slot: int = -1


@dataclass(frozen=True, slots=True)
class PassBuildInfo:
    """
    Metadata returned by build() to help the graph compiler.

    Attributes:
        pass_id: Stable identifier used for replacement and ordering.
        reads: Declared resource reads.
        writes: Declared resource writes.
    """

    pass_id: PassId
    reads: List[PassResourceUse]
    writes: List[PassResourceUse]


@dataclass
class RenderPass(ABC):
    """
    Abstract base class for all render passes.
    """

    pass_id: PassId

    @abstractmethod
    def build(self) -> PassBuildInfo:
        """Declare resource reads/writes and pass identity for compilation."""
        pass

    def on_compile(
        self, ctx: moderngl.Context, services: RenderServices
    ) -> None:
        """
        Called once when the graph is compiled.
        Use this to compile internal shaders or create private VAOs.
        """
        pass

    def execute(self, ctx: PassExecutionContext) -> None:
        """Execute the pass for the current frame."""
        pass

    def on_resize(self, width: int, height: int) -> None:
        """Called when pipeline resolution changes."""
        pass

    def on_destroy(self) -> None:
        """
        Called before graph teardown.
         release pass-owned GPU resources.
        """
        pass
