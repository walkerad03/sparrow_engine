# sparrow/graphics/graph/pass_base.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Literal,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    runtime_checkable,
)

import moderngl

from sparrow.core.components import RenderSettings
from sparrow.graphics.assets.material_manager import MaterialManager
from sparrow.graphics.assets.mesh_manager import MeshManager
from sparrow.graphics.assets.texture_manager import TextureManager
from sparrow.graphics.ecs.frame_submit import RenderFrameInput
from sparrow.graphics.graph.resources import GraphResource
from sparrow.graphics.shaders.shader_manager import ShaderManager
from sparrow.graphics.util.ids import PassId, ResourceId, get_pass_fbo_id


@dataclass(frozen=True, slots=True)
class PassResourceUse:
    """
    Declares how a pass uses a resource.

    The graph compiler uses this to:
      - validate that producers exist
      - order passes (deps)
      - detect write hazards
    """

    resource: ResourceId
    access: Literal["read", "write", "readwrite"]
    stage: str  # "color", "depth", "storage", "uniform", etc
    binding: Optional[int] = None


@dataclass(frozen=True, slots=True)
class PassBuildInfo:
    """
    Static info used at graph compile time.

    Attributes:
        pass_id: Stable identifier used for replacement and ordering.
        name: Human-readable name (used for debugging/profiling).
        reads: Declared resource reads.
        writes: Declared resource writes.
    """

    pass_id: PassId
    name: str
    reads: Sequence[PassResourceUse]
    writes: Sequence[PassResourceUse]


@dataclass(frozen=True, slots=True)
class RenderServices:
    """
    Typed access to commonly used renderer services.

    This avoids stringly-typed lookups in passes while still allowing extension.

    Attributes:
        shader_manager: Compiles/caches shader programs.
        mesh_manager: Provides VAOs/VBOs/IBOs.
        material_manager: Provides material parameters and texture bindings.
        texture_manager: Provides non-graph textures (asset textures, cubemaps, etc.).
        extras: Optional additional services keyed by name.
    """

    shader_manager: ShaderManager
    mesh_manager: MeshManager
    material_manager: MaterialManager
    texture_manager: TextureManager
    extras: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PassExecutionContext:
    """
    Runtime context provided to passes.

    Passes should treat this as read-only for the duration of `execute()`.

    Attributes:
        gl: Active ModernGL context.
        frame: Per-frame scene submission data (camera, draws, lights, debug flags).
        resources: Graph-owned GPU resources keyed by ResourceId.
        services: Typed access to shared managers/services.
        viewport_width: Current window framebuffer width in pixels.
        viewport_height: Current window framebuffer height in pixels.

    Notes:
        Most passes should render to graph-owned textures sized at the renderer's
        internal resolution and only the final present pass should care about the
        window viewport. If you later add logical vs window resolution, this
        context should be extended to include logical_width/logical_height and a
        present viewport rectangle.
    """

    gl: moderngl.Context
    frame: RenderFrameInput
    resources: Mapping[ResourceId, GraphResource[object]]
    services: RenderServices
    viewport_width: int
    viewport_height: int


@runtime_checkable
class RenderPass(Protocol):
    """
    A render graph pass.

    Contract:
        - `build()` declares the pass id/name and resource reads/writes.
        - `on_graph_compiled()` is called after resources exist; compile shaders, cache locations.
        - `execute()` issues GPU commands for a single frame.
        - `on_graph_destroyed()` releases pass-owned state (if any).

    Passes should be small and composable. heavy scene processing belongs in ECS
    extraction systems, not in `execute()`.
    """

    pass_id: PassId
    settings: RenderSettings

    @property
    def output_fbo_id(self) -> ResourceId:
        """Standardized FBO lookup ID."""
        return get_pass_fbo_id(self.pass_id)

    @property
    def output_target(self) -> ResourceId | None:
        """
        If None, the pass targets the screen.
        If it returns a ResourceId, the compiler uses that as the primary
        color attachment to build the auto-FBO.
        """
        ...

    def build(self) -> PassBuildInfo:
        """Declare resource reads/writes and pass identity for compilation."""
        ...

    def on_graph_compiled(
        self,
        *,
        ctx: moderngl.Context,
        resources: Mapping[ResourceId, GraphResource[object]],
        services: RenderServices,
    ) -> None:
        """
        Called after compilation (and any resource allocations) so the pass can
        create pipelines/programs, cache locations, etc.
        """
        ...

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        """Execute the pass for the current frame."""
        ...

    def on_graph_destroyed(self) -> None:
        """Called when the graph is torn down or pass is removed."""
        ...
