# sparrow/graphics/utils/geometry.py
import array

import moderngl


def create_fullscreen_triangle(ctx: moderngl.Context) -> moderngl.Buffer:
    """
    Create a vertex buffer for a fullscreen triangle (Screen Space).

    Vertices (x, y): (-1, -1), (3, -1), (-1, 3)
    This covers the [0,0] to [1,1] UV space effectively with a single triangle.
    """
    # 3 vertices, 2 floats each
    vertices = array.array(
        "f",
        [-1.0, -1.0, 3.0, -1.0, -1.0, 3.0],
    )
    return ctx.buffer(vertices)


def create_screen_quad(ctx: moderngl.Context) -> moderngl.Buffer:
    """
    Create a vertex buffer for a standard quad (-1 to 1).
    Format: x, y, u, v
    """
    # 4 verts, Triangle Strip
    # x, y, u, v
    data = array.array(
        "f",
        [
            -1.0,
            1.0,
            0.0,
            1.0,  # TL
            -1.0,
            -1.0,
            0.0,
            0.0,  # BL
            1.0,
            1.0,
            1.0,
            1.0,  # TR
            1.0,
            -1.0,
            1.0,
            0.0,  # BR
        ],
    )
    return ctx.buffer(data)


def create_cube(ctx: moderngl.Context, size: float = 1.0) -> moderngl.Buffer:
    """
    Create a generic cube vertex buffer (Pos, Normal, UV).
    Useful for debug rendering or skyboxes.
    """
    # TODO: THIS IMPLEMENTATION
    raise NotImplementedError
