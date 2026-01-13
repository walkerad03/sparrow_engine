# sparrow/graphics/debug/dump.py
from __future__ import annotations

import moderngl

from sparrow.graphics.graph.render_graph import CompiledRenderGraph


def dump_render_graph_state(
    *,
    graph: CompiledRenderGraph,
    gl: moderngl.Context,
    header: str = "RENDER GRAPH DEBUG DUMP",
) -> None:
    """
    Dump a comprehensive snapshot of render graph + GL state.

    Safe to call at runtime. Intended for debugging black screens,
    missing passes, incorrect bindings, and resource mismatches.
    """

    print("\n" + "=" * 80)
    print(header)
    print("=" * 80)

    # ------------------------------------------------------------------
    # Context info
    # ------------------------------------------------------------------

    print("\n[Context]")
    print(f"  GL Version      : {gl.version_code}")
    print(f"  Vendor          : {gl.info.get('GL_VENDOR', 'unknown')}")
    print(f"  Renderer        : {gl.info.get('GL_RENDERER', 'unknown')}")
    print(f"  Default FBO     : {gl.fbo}")
    print(f"  Viewport        : {gl.viewport}")

    # ------------------------------------------------------------------
    # Graph overview
    # ------------------------------------------------------------------

    print("\n[Render Graph]")
    print(f"  Pass count      : {len(graph.pass_order)}")
    print(f"  Resource count  : {len(graph.resources)}")

    print("\n  Pass order:")
    for i, pid in enumerate(graph.pass_order):
        print(f"    {i:02d}: {pid}")

    # ------------------------------------------------------------------
    # Pass details
    # ------------------------------------------------------------------

    print("\n[Passes]")
    for pid in graph.pass_order:
        p = graph.passes[pid]
        print(f"\n  Pass '{pid}'")
        print(f"    Type          : {type(p).__name__}")

        # Try to introspect build info if possible
        try:
            bi = p.build()
            print(f"    Declared name : {bi.name}")
            print(f"    Reads         : {[str(u.resource) for u in bi.reads]}")
            print(f"    Writes        : {[str(u.resource) for u in bi.writes]}")
        except Exception as e:
            print(f"    build() failed: {e}")

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------

    print("\n[Resources]")
    for rid, res in graph.resources.items():
        print(f"\n  Resource '{rid}'")
        print(f"    Type          : {type(res).__name__}")
        print(f"    Label         : {getattr(res, 'label', '<none>')}")

        handle = getattr(res, "handle", None)
        if handle is None:
            print("    Handle        : <none>")
            continue

        print(f"    Handle type   : {type(handle).__name__}")
        print(f"    Handle id     : {id(handle)}")

        # Texture-specific info
        if isinstance(handle, (moderngl.Texture, moderngl.TextureCube)):
            print("    [Texture]")
            print(f"      Size        : {handle.size}")
            print(f"      Components  : {handle.components}")
            print(f"      DType       : {handle.dtype}")
            print(f"      Samples     : {getattr(handle, 'samples', 1)}")
            print(f"      Filter      : {handle.filter}")
            print(f"      Repeat X/Y  : {handle.repeat_x}/{handle.repeat_y}")
            print(f"      Swizzle     : {handle.swizzle}")

        # Buffer-specific info
        if isinstance(handle, moderngl.Buffer):
            print("    [Buffer]")
            print(f"      Size        : {handle.size}")

        # Framebuffer-specific info
        if isinstance(handle, moderngl.Framebuffer):
            print("    [Framebuffer]")
            print(f"      Color atts  : {len(handle.color_attachments)}")
            print(f"      Depth att   : {handle.depth_attachment is not None}")

    # ------------------------------------------------------------------
    # Shader / program sanity (ModernGL-safe)
    # ------------------------------------------------------------------

    print("\n[Programs / Shaders]")
    for pid in graph.pass_order:
        p = graph.passes[pid]
        prog = getattr(p, "_program", None)
        if prog is None:
            continue

        print(f"\n  Pass '{pid}' program")
        print(f"    Program id    : {id(prog)}")

        # Uniforms (ModernGL-safe)
        try:
            uniforms = list(prog)
            print(f"    Uniforms      : {uniforms}")
            for name in uniforms:
                try:
                    u = prog[name]
                    if hasattr(u, "value"):
                        print(f"      {name} = {u.value}")
                except Exception:
                    pass
        except Exception as e:
            print(f"    Uniform query failed: {e}")

        print("    Program linked : yes")

    # ------------------------------------------------------------------
    # GL state that commonly breaks rendering
    # ------------------------------------------------------------------

    print("\n[GL State]")
    # print(f"  DEPTH_TEST     : {'enabled' if gl.depth_test else 'disabled'}")
    print(f"  CULL_FACE      : {'enabled' if gl.cull_face else 'disabled'}")
    # print(f"  BLEND          : {'enabled' if gl.blend else 'disabled'}")
    print(f"  SCISSOR_TEST   : {'enabled' if gl.scissor else 'disabled'}")

    print("\n" + "=" * 80)
    print("END RENDER GRAPH DEBUG DUMP")
    print("=" * 80 + "\n")
