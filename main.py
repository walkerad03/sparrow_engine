"""
Minimal renderer testing framework.

Run mode:
    - "blit": just show a generated gradient texture (tests graph, textures, tonemap)
    - "forward": draw a triangle (tests mesh path)
    - "deferred": run gbuffer + lighting (tests default deferred pipeline)

Expected keys:
    - ESC: quit
    - R: rebuild graph (exercise pipeline modification API)
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import Literal

import moderngl
import numpy as np
import pygame

from sparrow.graphics.ecs.frame_submit import CameraData, RenderFrameInput
from sparrow.graphics.renderer.deferred_renderer import DeferredRenderer
from sparrow.graphics.renderer.settings import (
    DeferredRendererSettings,
    PresentScaleMode,
    ResolutionSettings,
)


@dataclass(slots=True)
class AppState:
    mode: Literal["blit", "forward", "deferred"]
    frame_index: int = 0
    last_time: float = time.perf_counter()


def make_dummy_camera(w: int, h: int) -> CameraData:
    """Create a simple camera; to be replaced with math utils later."""
    view = np.eye(4, dtype=np.float32)
    proj = np.eye(4, dtype=np.float32)
    vp = proj @ view
    return CameraData(
        view=view,
        proj=proj,
        view_proj=vp,
        position_ws=np.array([0.0, 0.0, 2.0], dtype=np.float32),
        near=0.1,
        far=100.0,
    )


def _handle_pygame_events() -> None:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit(0)


def main() -> None:
    """Main entrypoint for the minimal renderer test app."""
    # 1) Create window + ModernGL context.
    window_width, window_height = 1280, 720

    pygame.init()
    pygame.display.set_mode(
        (window_width, window_height),
        pygame.OPENGL | pygame.DOUBLEBUF,
    )

    ctx = moderngl.create_context(460)
    gl_version = ctx.version_code
    print(f"OpenGL version {str(gl_version)[0]}.{str(gl_version)[1:]}")

    state = AppState(mode="blit")

    settings = DeferredRendererSettings(
        resolution=ResolutionSettings(
            logical_width=320,
            logical_height=320,
            scale_mode=PresentScaleMode.INTEGER_FIT,
        ),
        hdr=True,
        msaa_samples=1,
        enable_debug_views=False,
    )

    renderer = DeferredRenderer(ctx, settings=settings, emit_event=None)
    renderer.initialize()

    running = True
    while running:
        _handle_pygame_events()

        now = time.perf_counter()
        dt = now - state.last_time
        state.last_time = now
        state.frame_index += 1

        # 2) Poll input, window events, resize handling.
        # If resized, update renderer settings and rebuild graph or trigger resize path.

        cam = make_dummy_camera(window_width, window_height)

        # 3) Build a frame input. For early phases, lights and draws can be empty.
        frame = RenderFrameInput(
            frame_index=state.frame_index,
            dt_seconds=dt,
            camera=cam,
            draws=[],
            point_lights=[],
            debug_flags={"mode_blit": state.mode == "blit"},
            viewport_width=window_width,
            viewport_height=window_height,
        )

        renderer.render_frame(frame)

        # 4) Present buffers.
        pygame.display.flip()

        # 5) Optional: throttle
        # time.sleep(0.001)

    # renderer.shutdown if it exists


if __name__ == "__main__":
    main()
