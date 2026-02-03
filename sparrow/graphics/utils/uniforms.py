# sparrow/graphics/utils/uniforms.py
import struct
from typing import Any

import moderngl
import numpy as np

# std140 Alignment Rules:
# Scalar (int, bool, float) = 4 bytes (N=4)
# Vec2 = 8 bytes (2N)
# Vec3 = 16 bytes (4N) - Hardware treats vec3 as vec4
# Vec4 = 16 bytes (4N)
# Mat4 = 64 bytes (Array of 4 Vec4s)


def pack_float(val: float) -> bytes:
    return struct.pack("f", val)


def pack_int(val: int) -> bytes:
    return struct.pack("i", val)


def pack_vec2(x: float, y: float) -> bytes:
    return struct.pack("2f", x, y)


def pack_vec3(x: float, y: float, z: float) -> bytes:
    """
    Packs a vec3.
    Note: In std140, a vec3 in a struct usually requires 16-byte alignment (padding float).
    Use pack_vec3_std140 for UBOs.
    """
    return struct.pack("3f", x, y, z)


def pack_vec3_std140(x: float, y: float, z: float) -> bytes:
    """Packs vec3 with 4th float padding (16 bytes total)."""
    return struct.pack("3f x", x, y, z)


def pack_vec4(x: float, y: float, z: float, w: float) -> bytes:
    return struct.pack("4f", x, y, z, w)


def pack_mat4(mat: np.ndarray) -> bytes:
    """
    Packs a 4x4 numpy matrix (casts to float32).
    Expects column-major if using standard OpenGL shaders,
    but numpy is row-major. Usually require .T or explicit transpose in shader.
    """
    # flatten() returns row-major by default.
    # If your shader expects column-major (standard), ensure mat is transposed correctly before packing.
    if mat.shape != (4, 4):
        raise ValueError("Matrix must be 4x4")
    return mat.astype("f4").tobytes()


def set_uniform(
    program: moderngl.Program | None, name: str, value: Any
) -> None:
    if not program:
        return

    if name not in program:
        return

    member = program[name]

    if isinstance(member, moderngl.Uniform):
        if isinstance(value, bytes):
            member.write(value)
        else:
            member.value = value
