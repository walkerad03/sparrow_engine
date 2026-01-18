from __future__ import annotations

from typing import TYPE_CHECKING, List

import pygame

from sparrow.core.components import Mesh, Transform
from sparrow.core.world import World
from sparrow.graphics.ecs.frame_submit import DrawItem, RenderFrameInput
from sparrow.graphics.renderer.settings import (
    PresentScaleMode,
    RaytracingRendererSettings,
    ResolutionSettings,
    SunlightSettings,
)
from sparrow.input.context import InputContext
from sparrow.input.handler import InputHandler
from sparrow.resources.cameras import CameraOutput
from sparrow.resources.rendering import (
    RenderContext,
    RendererSettingsResource,
    RenderFrame,
    RenderViewport,
)
from sparrow.systems.camera import camera_system
from sparrow.systems.rendering import ensure_renderer_resource, render_system

if TYPE_CHECKING:
    from sparrow.core.application import Application


class Scene:
    render_enabled: bool = True

    def __init__(self, app: Application):
        self.world = World()

        self.app = app

        self.frame_index = 0
        self.last_time = 0

        input_handler = InputHandler()
        self.world.add_resource(input_handler)

        base_ctx = InputContext("default")
        base_ctx.bind(pygame.K_w, "UP")
        base_ctx.bind(pygame.K_s, "DOWN")
        base_ctx.bind(pygame.K_a, "LEFT")
        base_ctx.bind(pygame.K_d, "RIGHT")
        base_ctx.bind(pygame.K_SPACE, "SPACE")

        input_handler.push_context(base_ctx)

        self.world.add_resource(CameraOutput())

    def on_start(self) -> None:
        """Called when the scene is first activated."""
        pass

    def on_update(self, dt: float) -> None:
        """Called every frame to update game logic."""
        self.frame_index += 1

        camera_system(self.world)

        # TODO: Poll input, window events, resize handling.
        # If resized, update renderer settings and rebuild graph or trigger resize path.

    def on_render(self) -> None:
        """Called every frame to submit render data (if rendering is enabled)."""
        if not self.render_enabled:
            return

        frame = self.get_render_frame()
        frame_res = RenderFrame(frame)

        if self.world.try_resource(RenderFrame) is None:
            self.world.add_resource(frame_res)
        else:
            self.world.mutate_resource(frame_res)

        render_system(self.world)

    def on_exit(self) -> None:
        """Called when transitioning away from this scene."""
        pass

    def configure_rendering(self) -> None:
        if not self.render_enabled:
            return

        if self.world.try_resource(RenderContext) is None:
            raise RuntimeError("RenderContext resource missing for renderer setup.")

        if self.world.try_resource(RendererSettingsResource) is None:
            viewport = self.world.try_resource(RenderViewport)
            if viewport is None:
                raise RuntimeError(
                    "RenderViewport resource missing for renderer setup."
                )

            resolution = ResolutionSettings(
                logical_width=int(viewport.width / 1),
                logical_height=int(viewport.height / 1),
                scale_mode=PresentScaleMode.INTEGER_FIT,
            )

            settings = RaytracingRendererSettings(
                resolution,
                SunlightSettings(),
                samples_per_pixel=16,
                denoiser_enabled=False,
            )
            self.world.add_resource(RendererSettingsResource(settings))

        ensure_renderer_resource(self.world)

    def get_render_frame(self) -> RenderFrameInput:
        """
        Extracts data from the ECS World to build the FrameContext for the Renderer.
        You can override this if you need custom render logic.
        """
        viewport = self.world.try_resource(RenderViewport)
        if viewport is None:
            raise RuntimeError("RenderViewport resource missing for render frame.")

        w, h = viewport.width, viewport.height

        cam_out = self.world.try_resource(CameraOutput)
        if cam_out is None or cam_out.active is None:
            raise RuntimeError("No active camera")

        draws: List[DrawItem] = []
        draw_id = 0
        for eid, mesh, transform in self.world.join(Mesh, Transform):
            draws.append(
                DrawItem(
                    mesh.mesh_id,
                    mesh.material_id,
                    transform.matrix_transform,
                    draw_id,
                )
            )
            draw_id += 1

        return RenderFrameInput(
            frame_index=self.frame_index,
            dt_seconds=1 / 60,
            camera=cam_out.active,
            draws=draws,
            point_lights=[],
            viewport_width=w,
            viewport_height=h,
        )
