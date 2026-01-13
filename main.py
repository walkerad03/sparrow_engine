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

import struct
import sys
import time
from dataclasses import dataclass
from typing import List, Literal

import moderngl
import numpy as np
import pygame

from sparrow.graphics.api.renderer_api import RendererAPI
from sparrow.graphics.assets.material_manager import Material
from sparrow.graphics.assets.types import MeshData, VertexLayout
from sparrow.graphics.ecs.frame_submit import CameraData, DrawItem, RenderFrameInput
from sparrow.graphics.graph.resources import TextureDesc
from sparrow.graphics.passes.forward_tonemap import ForwardTonemapPass
from sparrow.graphics.passes.forward_unlit import ForwardUnlitPass
from sparrow.graphics.renderer.deferred_renderer import DeferredRenderer
from sparrow.graphics.renderer.settings import (
    DeferredRendererSettings,
    PresentScaleMode,
    ResolutionSettings,
)
from sparrow.graphics.util.ids import MaterialId, MeshId, PassId, ResourceId


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
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit(0)


def main() -> None:
    """Main entrypoint for the minimal renderer test app."""
    # 1) Create window + ModernGL context.
    window_width, window_height = 1920, 1080

    pygame.init()
    pygame.display.set_mode(
        (window_width, window_height),
        pygame.OPENGL | pygame.DOUBLEBUF | pygame.FULLSCREEN | pygame.SCALED,
    )

    ctx = moderngl.create_context(460)
    gl_version = ctx.version_code
    print(f"OpenGL version {str(gl_version)[0]}.{str(gl_version)[1:]}")

    state = AppState(mode="blit")

    settings = DeferredRendererSettings(
        resolution=ResolutionSettings(
            logical_width=int(1920 / 4),
            logical_height=int(1080 / 4),
            scale_mode=PresentScaleMode.INTEGER_FIT,
        ),
        hdr=True,
        msaa_samples=1,
        enable_debug_views=False,
    )

    renderer = DeferredRenderer(ctx, settings=settings, emit_event=None)
    renderer.initialize()

    triangle_mesh_id = MeshId("triangle")
    triangle_mesh = MeshData(
        vertices=struct.pack("6f", -0.6, -0.6, 0.6, -0.6, 0.0, 0.6),
        indices=None,
        vertex_layout=VertexLayout(attributes=["in_pos"], format="2f", stride_bytes=8),
    )
    renderer.mesh_manager.create(triangle_mesh_id, triangle_mesh, label="Test Triangle")

    mat_red_id = MaterialId("mat_red")
    renderer.material_manager.create(
        mat_red_id,
        Material(base_color_factor=(1.0, 0.0, 0.0, 1.0)),
    )

    draws: List[DrawItem] = [
        DrawItem(
            triangle_mesh_id,
            mat_red_id,
            np.eye(4, dtype=np.float32),
            1,
        )
    ]

    api = RendererAPI(renderer)
    edit = api.begin_graph_edit(reason="set_default_pipeline")

    hdr_res_id = ResourceId("hdr_color")
    edit.add_texture(
        hdr_res_id,
        TextureDesc(
            width=1920,
            height=1080,
            components=4,
            dtype="f2",
            label="HDR Color",
        ),
    )

    forward_pass_id = PassId("forward")
    forward_pass = ForwardUnlitPass(
        pass_id=forward_pass_id,
        color_target=hdr_res_id,
    )
    edit.add_pass(forward_pass_id, forward_pass)

    tonemap_pass_id = PassId("tonemap")
    tonemap_pass = ForwardTonemapPass(
        pass_id=tonemap_pass_id,
        hdr_input=hdr_res_id,
    )
    edit.add_pass(tonemap_pass_id, tonemap_pass)

    edit.commit()

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

        frame = RenderFrameInput(
            frame_index=state.frame_index,
            dt_seconds=dt,
            camera=cam,
            draws=draws,
            point_lights=[],
            debug_flags={"mode_blit": state.mode == "blit"},
            viewport_width=window_width,
            viewport_height=window_height,
        )

        renderer.render_frame(frame)
        pygame.display.flip()

    # renderer.shutdown if it exists


if __name__ == "__main__":
    main()
