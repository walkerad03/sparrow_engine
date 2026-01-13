# sparrow/graphics/passes/debug_present.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

import moderngl

from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
    RenderServices,
)
from sparrow.graphics.graph.resources import (
    FramebufferResource,
    GraphResource,
    TextureResource,
    expect_resource,
)
from sparrow.graphics.helpers.fullscreen import create_fullscreen_triangle
from sparrow.graphics.shaders.program_types import ShaderStages
from sparrow.graphics.shaders.shader_manager import ShaderRequest
from sparrow.graphics.util.ids import PassId, ResourceId, ShaderId


@dataclass(slots=True)
class DebugPresentPass(RenderPass):
    """
    Debug pass to present a chosen graph texture to the window framebuffer.

    This is intended for bring-up and inspection of intermediate render targets
    (e.g., GBuffer attachments, HDR lighting buffer).

    Reads:
        - `source_tex` (TextureResource)

    Writes:
        - None (writes to the default framebuffer / swapchain via gl.screen)

    Notes:
        - This pass binds gl.screen and draws a fullscreen triangle.
        - It can optionally source the texture from a framebuffer resource by index.
          (Most robust is to pass the texture ResourceId directly.)
    """

    pass_id: PassId

    # Preferred: directly present a texture resource.
    source_tex: Optional[ResourceId] = None

    # Optional convenience: select from an FBO's color attachments by index.
    # If provided and `source_tex` is None, we'll pull texture from `source_fbo`.
    source_fbo: Optional[ResourceId] = None
    color_index: int = 0

    # Optional: force nearest sampling (useful for pixel-art / inspecting buffers).
    nearest: bool = True

    _program: moderngl.Program | None = None
    _vao: moderngl.VertexArray | None = None
    _vbo: moderngl.Buffer | None = None
    _u_tex: moderngl.Uniform | None = None

    def build(self) -> PassBuildInfo:
        reads: list[PassResourceUse] = []
        if self.source_tex is not None:
            reads.append(
                PassResourceUse(self.source_tex, "read", stage="texture", binding=0)
            )
        if self.source_fbo is not None:
            reads.append(PassResourceUse(self.source_fbo, "read", stage="framebuffer"))

        return PassBuildInfo(
            pass_id=self.pass_id,
            name="Debug Present",
            reads=reads,
            writes=[],
        )

    def on_graph_compiled(
        self,
        *,
        ctx: moderngl.Context,
        resources: Mapping[ResourceId, GraphResource[object]],
        services: RenderServices,
    ) -> None:
        shader_mgr = services.shader_manager

        req = ShaderRequest(
            shader_id=ShaderId("debug_present"),
            stages=ShaderStages(
                vertex="sparrow/graphics/shaders/default/debug_present.vert",
                fragment="sparrow/graphics/shaders/default/debug_present.frag",
            ),
            label="DebugPresent",
        )

        prog = shader_mgr.get(req).program
        assert isinstance(prog, moderngl.Program)

        # Cache uniform (typed)
        u_tex = prog.get("u_tex", None)
        if u_tex is None or not isinstance(u_tex, moderngl.Uniform):
            raise RuntimeError(
                "debug_present shader must declare uniform sampler2D u_tex"
            )

        vbo = create_fullscreen_triangle(ctx)
        vao = ctx.vertex_array(prog, [(vbo, "2f", "in_pos")])

        self._program = prog
        self._u_tex = u_tex
        self._vbo = vbo
        self._vao = vao

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        gl = exec_ctx.gl

        gl.disable(moderngl.DEPTH_TEST)

        assert self._program is not None
        assert self._vao is not None
        assert self._u_tex is not None

        # Resolve the texture resource we will present.
        tex: moderngl.Texture

        if self.source_tex is not None:
            tex_res = expect_resource(
                exec_ctx.resources, self.source_tex, TextureResource
            )
            # We only support 2D textures for this debug pass.
            if not isinstance(tex_res.handle, moderngl.Texture):
                raise TypeError(
                    f"DebugPresentPass expected Texture (2D) for '{self.source_tex}', "
                    f"got {type(tex_res.handle).__name__}"
                )
            tex = tex_res.handle

        elif self.source_fbo is not None:
            fbo_res = expect_resource(
                exec_ctx.resources, self.source_fbo, FramebufferResource
            )
            fbo = fbo_res.handle
            # ModernGL exposes framebuffer color attachments in `color_attachments`.
            # This is a tuple of Texture/Renderbuffer.
            atts = getattr(fbo, "color_attachments", None)
            if atts is None:
                raise RuntimeError(
                    "Framebuffer has no color_attachments attribute in this ModernGL version"
                )

            if not (0 <= self.color_index < len(atts)):
                raise IndexError(
                    f"color_index {self.color_index} out of range for framebuffer "
                    f"with {len(atts)} color attachments"
                )

            att = atts[self.color_index]
            if not isinstance(att, moderngl.Texture):
                raise TypeError(
                    f"DebugPresentPass expected Texture attachment at index {self.color_index}, "
                    f"got {type(att).__name__}"
                )
            tex = att

        else:
            raise RuntimeError(
                "DebugPresentPass requires either source_tex or source_fbo"
            )

        # Bind default framebuffer (window) and set viewport.
        gl.screen.use()
        gl.viewport = (0, 0, exec_ctx.viewport_width, exec_ctx.viewport_height)

        # Optional: clear so you can see if nothing draws.
        gl.clear(0.0, 0.0, 0.0, 1.0)

        # Sampling mode (handy for inspecting buffers and pixel art).
        if self.nearest:
            tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        else:
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)

        # Bind texture to unit 0 and point sampler at unit 0.
        tex.use(location=0)
        self._u_tex.value = 0  # typed uniform, OK

        # Draw fullscreen triangle.
        self._vao.render(mode=moderngl.TRIANGLES)

    def on_graph_destroyed(self) -> None:
        # Pass-owned GPU objects; let GC handle unless you prefer explicit release.
        self._vao = None
        self._vbo = None
        self._program = None
        self._u_tex = None
