# sparrow/graphics/graph/pass_base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Flag, auto
from math import floor, log2
from typing import (
    Any,
    Literal,
    Mapping,
    Optional,
    Sequence,
)

import moderngl
import numpy as np

from sparrow.graphics.assets.material_manager import MaterialManager
from sparrow.graphics.assets.mesh_manager import MeshManager
from sparrow.graphics.assets.texture_manager import TextureManager
from sparrow.graphics.ecs.frame_submit import RenderFrameInput
from sparrow.graphics.graph.resources import GraphResource
from sparrow.graphics.renderer.settings import RendererSettings
from sparrow.graphics.shaders.shader_manager import ShaderManager
from sparrow.graphics.util.ids import PassId, ResourceId, TextureId, get_pass_fbo_id


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


class PassFeatures(Flag):
    NONE = 0
    CAMERA = auto()
    SUN = auto()
    RESOLUTION = auto()
    TIME = auto()


@dataclass(slots=True)
class RenderPass(ABC):
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
    settings: RendererSettings

    features: PassFeatures = PassFeatures.NONE

    _program: Optional[moderngl.Program | moderngl.ComputeShader] = None
    _uniforms: dict[str, moderngl.Uniform] = field(default_factory=dict)

    _sky_lut_binding: int = 5

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
        return None

    def _get_uniform(self, name: str) -> moderngl.Uniform | None:
        if not self._program:
            return None
        obj = self._program.get(name, None)
        return obj if isinstance(obj, moderngl.Uniform) else None

    def _set_sampler(self, name: str, unit: int) -> None:
        u = self._get_uniform(name)
        if u is not None:
            u.value = unit

    @abstractmethod
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
        Base implementation of resource compilation.

        Called after compilation (and any resource allocations) so the pass can
        create pipelines/programs, cache locations, etc.

        Child classes MUST call super().on_graph_compiled() if they override this.
        Assume that the child class will set self._program prior to running.
        """
        if not self._program:
            return

        if PassFeatures.CAMERA in self.features:
            for name in ["u_camera_pos", "u_inv_view_proj", "u_view_proj"]:
                if name in self._program:
                    self._uniforms[name] = self._program[name]

        if PassFeatures.SUN in self.features:
            for name in [
                "u_sun_direction",
                "u_sun_color",
                "u_sky_lut",
                "u_sky_max_mip",
                "u_sun_radiance",
            ]:
                if name in self._program:
                    self._uniforms[name] = self._program[name]

        if PassFeatures.RESOLUTION in self.features and "u_resolution" in self._program:
            self._uniforms["u_resolution"] = self._program["u_resolution"]

        if PassFeatures.TIME in self.features and "u_frame_index" in self._program:
            self._uniforms["u_frame_index"] = self._program["u_frame_index"]

    def execute_base(self, exec_ctx: PassExecutionContext) -> None:
        """
        Call this at the START of your child execute() method.
        Handles all global state uploads.
        """
        if not self._program:
            return

        assert self._program is not None

        services = exec_ctx.services
        frame = exec_ctx.frame

        # Update camera
        if PassFeatures.CAMERA in self.features:
            cam = exec_ctx.frame.camera
            if "u_camera_pos" in self._uniforms:
                self._uniforms["u_camera_pos"].value = tuple(cam.position_ws)
            if "u_inv_view_proj" in self._uniforms:
                inv_vp = np.linalg.inv(cam.view_proj).astype(np.float32)
                self._uniforms["u_inv_view_proj"].write(inv_vp.T.tobytes())
            if "u_view_proj" in self._uniforms:
                vp = cam.view_proj.astype(np.float32)
                self._uniforms["u_view_proj"].write(vp.T.tobytes())

        # Directional lighting updates
        if PassFeatures.SUN in self.features:
            sun = self.settings.sunlight
            if "u_sun_direction" in self._uniforms:
                self._uniforms["u_sun_direction"].value = tuple(sun.direction)
            if "u_sun_color" in self._uniforms:
                self._uniforms["u_sun_color"].value = tuple(sun.color)

            if "u_sky_lut" in self._uniforms:
                tex_id = TextureId("engine.sky_lut")
                sky_handle = services.texture_manager.get(tex_id)
                sky_handle.texture.use(location=self._sky_lut_binding)
                self._uniforms["u_sky_lut"].value = self._sky_lut_binding

            if "u_sky_max_mip" in self._uniforms:
                h, w = (
                    self.settings.resolution.logical_height,
                    self.settings.resolution.logical_width,
                )

                max_mips = floor(log2(max(h, w)))
                self._uniforms["u_sky_max_mip"].value = float(max_mips)

            if "u_sun_radiance" in self._uniforms:
                self._uniforms["u_sun_radiance"].value = (10.0, 10.0, 10.0)

        if (
            PassFeatures.RESOLUTION in self.features
            and "u_resolution" in self._uniforms
        ):
            self._uniforms["u_resolution"].value = (
                exec_ctx.viewport_width,
                exec_ctx.viewport_height,
            )

        if PassFeatures.TIME in self.features and "u_frame_index" in self._uniforms:
            self._uniforms["u_frame_index"].value = frame.frame_index

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        """Execute the pass for the current frame."""
        ...

    def on_graph_destroyed(self) -> None:
        """Called when the graph is torn down or pass is removed."""
        ...
