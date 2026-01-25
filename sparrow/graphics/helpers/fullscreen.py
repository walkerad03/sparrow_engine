# sparrow/graphics/helpers/fullscreen.py
from __future__ import annotations

import struct

import moderngl


def create_fullscreen_triangle(ctx: moderngl.Context) -> moderngl.Buffer:
    """
    Create a vertex buffer for a fullscreen triangle.

    The triangle is defined in clip space and covers the entire viewport.
    Intended for fullscreen post-processing and fullscreen deferred passes.

    Vertex positions (x, y):
        (-1, -1)
        (3, -1)
        (-1, 3)

    Returns:
        moderngl.Buffer: A buffer containing 3 vec2 positions (float64).
    """
    verts = (-1.0, -1.0, 3.0, -1.0, -1.0, 3.0)
    data = struct.pack("6d", *verts)

    return ctx.buffer(data)
