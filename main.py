"""
Minimal renderer testing framework.

Run mode: (Not implemented yet)
    - "blit": just show a generated gradient texture (tests graph, textures, tonemap)
    - "forward": draw a triangle (tests mesh path)
    - "deferred": run gbuffer + lighting (tests default deferred pipeline)

Expected keys:
    - ESC: quit
"""

from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal

import moderngl
import numpy as np
import pygame
from numpy.typing import NDArray

from sparrow.graphics.assets.material_manager import Material
from sparrow.graphics.assets.obj_loader import load_obj
from sparrow.graphics.debug.profiler import profile
from sparrow.graphics.ecs.frame_submit import (
    CameraData,
    DrawItem,
    LightPoint,
    RenderFrameInput,
)
from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.pipelines.deferred import build_deferred_pipeline
from sparrow.graphics.pipelines.forward import build_forward_pipeline
from sparrow.graphics.renderer.deferred_renderer import DeferredRenderer
from sparrow.graphics.renderer.settings import (
    DeferredRendererSettings,
    PresentScaleMode,
    ResolutionSettings,
)
from sparrow.graphics.util.ids import MaterialId, MeshId


@dataclass(slots=True)
class AppState:
    mode: Literal["blit", "forward", "deferred"]
    frame_index: int = 0
    last_time: float = time.perf_counter()


def make_simple_camera(
    eye: NDArray[np.float32],
    target: NDArray[np.float32],
    fov: float,
    w: int,
    h: int,
    near: float,
    far: float,
) -> CameraData:
    """
    Create a static camera.
    Optimized for per-frame execution by removing Numpy call overhead for vector math.
    """
    # 1. Unpack values to float scalars (faster than numpy indexing in loops)
    ex, ey, ez = float(eye[0]), float(eye[1]), float(eye[2])
    tx, ty, tz = float(target[0]), float(target[1]), float(target[2])

    # 2. Forward Vector (f = target - eye)
    fx, fy, fz = tx - ex, ty - ey, tz - ez

    # Normalize Forward
    # Pure python sqrt is faster than np.linalg.norm for single vector
    len_f = math.sqrt(fx * fx + fy * fy + fz * fz)
    inv_len_f = 1.0 / len_f if len_f > 1e-9 else 1.0
    fx, fy, fz = fx * inv_len_f, fy * inv_len_f, fz * inv_len_f

    # 3. Right Vector (s = cross(f, up))
    # Assuming Up is always (0, 1, 0), we can hardcode the cross product
    # s = (fz*up.y, 0, -fx*up.y) -> (-fz, 0, fx)
    sx, sy, sz = -fz, 0.0, fx

    # Normalize Right
    len_s_sq = sx * sx + sz * sz
    if len_s_sq < 1e-12:
        # Singularity: looking straight up/down
        sx, sy, sz = 1.0, 0.0, 0.0
    else:
        inv_len_s = 1.0 / math.sqrt(len_s_sq)
        sx, sy, sz = sx * inv_len_s, sy * inv_len_s, sz * inv_len_s

    # 4. Up Vector (u = cross(s, f)) (Recompute orthogonal up)
    # Standard cross product expansion
    ux = sy * fz - sz * fy
    uy = sz * fx - sx * fz
    uz = sx * fy - sy * fx

    # 5. Translation Dot Products
    # view[0,3] = -dot(s, eye)
    trans_s = -(sx * ex + sy * ey + sz * ez)
    # view[1,3] = -dot(u, eye)
    trans_u = -(ux * ex + uy * ey + uz * ez)
    # view[2,3] = dot(f, eye) (Recall: View Z is -f)
    trans_f = fx * ex + fy * ey + fz * ez

    # 6. Construct View Matrix directly (Single allocation)
    # Note: Row 2 is -f
    view = np.array(
        [
            [sx, sy, sz, trans_s],
            [ux, uy, uz, trans_u],
            [-fx, -fy, -fz, trans_f],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )

    # 7. Construct Projection Matrix
    aspect = w / h
    tan_half_fov = math.tan(math.radians(fov) * 0.5)
    fl = 1.0 / tan_half_fov

    inv_nf = 1.0 / (near - far)
    p22 = (far + near) * inv_nf
    p23 = (2.0 * far * near) * inv_nf

    proj = np.array(
        [
            [fl / aspect, 0.0, 0.0, 0.0],
            [0.0, fl, 0.0, 0.0],
            [0.0, 0.0, p22, p23],
            [0.0, 0.0, -1.0, 0.0],
        ],
        dtype=np.float32,
    )

    # 8. Optimized Matrix Multiply (Proj @ View)
    # Because Proj is sparse, we can calculate the result directly
    # faster than np.matmul(proj, view) for 4x4.

    # P00 * ViewRow0
    # P11 * ViewRow1
    # P22 * ViewRow2 + P23 * ViewRow3 (where ViewRow3 is 0,0,0,1)
    # -1  * ViewRow2

    p00 = fl / aspect
    p11 = fl

    vp = np.array(
        [
            [p00 * sx, p00 * sy, p00 * sz, p00 * trans_s],
            [p11 * ux, p11 * uy, p11 * uz, p11 * trans_u],
            [p22 * -fx, p22 * -fy, p22 * -fz, p22 * trans_f + p23],
            [fx, fy, fz, -trans_f],  # Row 3 is -1 * ViewRow2
        ],
        dtype=np.float32,
    )

    return CameraData(
        view=view,
        proj=proj,
        view_proj=vp,
        position_ws=eye,
        near=near,
        far=far,
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


PIPELINES = {
    "deferred": build_deferred_pipeline,
    "forward": build_forward_pipeline,
    # "blit": build_blit_pipeline
}


@profile(out_dir=Path(".debug"), enabled=True)
def main() -> None:
    """Main entrypoint for the minimal renderer test app."""
    # 1) Create window + ModernGL context.
    window_width, window_height = 1920, 1080

    pygame.init()
    pygame.display.set_mode(
        (window_width, window_height),
        pygame.OPENGL | pygame.DOUBLEBUF | pygame.FULLSCREEN | pygame.SCALED,
    )
    clock = pygame.Clock()

    ctx = moderngl.create_context(460)
    gl_version = ctx.version_code
    print(f"OpenGL version {str(gl_version)[0]}.{str(gl_version)[1:]}")

    state = AppState(mode="deferred")

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

    def configure_graph(builder: RenderGraphBuilder):
        if state.mode in PIPELINES:
            PIPELINES[state.mode](builder, window_width, window_height)
        else:
            raise ValueError(f"Unknown mode {state.mode}")

    renderer.rebuild_graph(configure_graph, reason=f"mode_{state.mode}")

    stormtrooper = MeshId("stormtrooper")
    renderer.mesh_manager.create(
        stormtrooper,
        load_obj("stormtrooper.obj"),
        label="Stormtrooper Helmet",
    )

    pbr_mat = MaterialId("pbr_mat")
    renderer.material_manager.create(
        pbr_mat,
        Material(
            roughness=0.1,
            base_color_factor=(1.0, 1.0, 1.0, 1.0),
            metalness=1.0,
        ),
    )

    draws: List[DrawItem] = [
        DrawItem(
            stormtrooper,
            pbr_mat,
            np.eye(4, dtype=np.float32),
            1,
        )
    ]

    # Static camera data
    eye = np.array([3.0, 1.0, 0.0], dtype=np.float32)
    target = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    fov = 10.0
    near = 0.1
    far = 100.0

    running = True
    t = 0
    while running:
        _handle_pygame_events()

        now = time.perf_counter()
        dt = now - state.last_time
        state.last_time = now
        state.frame_index += 1

        # 2) Poll input, window events, resize handling.
        # If resized, update renderer settings and rebuild graph or trigger resize path.

        cam = make_simple_camera(
            eye=eye,
            target=target,
            fov=fov,
            w=window_width,
            h=window_height,
            near=near,
            far=far,
        )
        """
        eye = np.array(
            [
                np.sin(t * 0.01) * 4.0,
                1.5,
                np.cos(t * 0.01) * 4.0,
            ],
            dtype=np.float32,
        )
        """
        k = t * 0.02

        point_lights = [
            LightPoint(
                np.array(
                    [
                        np.sin(t * 0.03) * 4.0,  # Base speed
                        np.cos(t * 0.07) * 3.0,  # 2.3x faster vertical bob
                        np.sin(t * 0.05) * 4.0,  # Different speed depth
                    ],
                    dtype=np.float32,
                ),
                10.0,
                np.array([1, 0, 0], dtype=np.float32),
                1.0,
            ),
            LightPoint(
                np.array(
                    [
                        (np.sin(k) + 2 * np.sin(2 * k)) * 1.5,  # X
                        (np.cos(k) - 2 * np.cos(2 * k)) * 1.5,  # Y
                        (-np.sin(3 * k)) * 1.5,  # Z
                    ],
                    dtype=np.float32,
                ),
                10.0,
                np.array([0, 0, 1], dtype=np.float32),
                1.0,
            ),
        ]

        frame = RenderFrameInput(
            frame_index=state.frame_index,
            dt_seconds=dt,
            camera=cam,
            draws=draws,
            point_lights=point_lights,
            debug_flags={"mode_blit": state.mode == "blit"},
            viewport_width=window_width,
            viewport_height=window_height,
        )

        renderer.render_frame(frame)
        pygame.display.flip()
        clock.tick(60)
        t += 1

    # renderer.shutdown if it exists


if __name__ == "__main__":
    main()
