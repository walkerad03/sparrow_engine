# sparrow/math.py
import math
from typing import TypeVar, Union

import numpy as np

from sparrow.types import Quaternion, Scalar, Vector2, Vector3

V = TypeVar("V", Vector2, Vector3)


def deg_to_rad(d: Scalar) -> Scalar:
    return d * math.pi / 180.0


# -- Vector Math --
def magnitude_vec(v: Union[Vector2, Vector3]) -> Scalar:
    return math.hypot(*v)


def norm_vec(v: Union[Vector2, Vector3]) -> Union[Vector2, Vector3]:
    mag = magnitude_vec(v)
    if mag == 0:
        return v
    return v / mag


def dist_vec(a: V, b: V) -> Scalar:
    return math.dist(a, b)


def dot_vec(a: V, b: V) -> Scalar:
    return sum(x * y for x, y in zip(a, b))


def cross_vec2(a: Vector2, b: Vector2) -> Scalar:
    return a.x * b.y - a.y * b.x


def cross_vec3(a: Vector3, b: Vector3) -> Vector3:
    return Vector3(
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    )


def rotate_vec2(v: Vector2, angle: Scalar) -> Vector2:
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    return Vector2(v.x * cos_a - v.y * sin_a, v.x * sin_a + v.y * cos_a)


def cross_product_vec3(a: Vector3, b: Vector3) -> Vector3:
    return Vector3(
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    )


def rotate_vec_by_quat(v: Vector3, q: Quaternion) -> Vector3:
    u = Vector3(q.x, q.y, q.z)
    s = q.w

    # 2.0 * dot(u, v) * u + (s*s - dot(u, u)) * v + 2.0 * s * cross(u, v)
    # Optimized: v + 2.0 * cross(u, cross(u, v) + s * v)

    uv = cross_product_vec3(u, v)
    uuv = cross_product_vec3(u, uv)

    return Vector3(
        v.x + 2.0 * (s * uv.x + uuv.x),
        v.y + 2.0 * (s * uv.y + uuv.y),
        v.z + 2.0 * (s * uv.z + uuv.z),
    )


def rotate_vec_by_quat_inv(v: Vector3, q: Quaternion) -> Vector3:
    # Inverse rotation uses conjugate quaternion (-x, -y, -z, w)
    u = Vector3(-q.x, -q.y, -q.z)
    s = q.w

    uv = cross_product_vec3(u, v)
    uuv = cross_product_vec3(u, uv)

    return Vector3(
        v.x + 2.0 * (s * uv.x + uuv.x),
        v.y + 2.0 * (s * uv.y + uuv.y),
        v.z + 2.0 * (s * uv.z + uuv.z),
    )


def batch_transform_to_matrix(
    pos: np.ndarray, rot: np.ndarray, scale: np.ndarray
) -> np.ndarray:
    """
    Vectorized calculation of Model Matrices.
    pos: (N, 3)
    rot: (N, 4) - Quaternions (x, y, z, w)
    scale: (N, 3)
    Returns: (N, 4, 4)
    """
    N = len(pos)

    # 1. Rotation Matrix from Quaternion (Vectorized)
    x, y, z, w = rot[:, 0], rot[:, 1], rot[:, 2], rot[:, 3]

    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z

    # Construct (N, 3, 3) Rotation Matrix
    # Formula: Standard Quaternion -> Matrix conversion
    R = np.zeros((N, 3, 3), dtype=np.float32)

    R[:, 0, 0] = 1.0 - 2.0 * (yy + zz)
    R[:, 0, 1] = 2.0 * (xy - wz)
    R[:, 0, 2] = 2.0 * (xz + wy)

    R[:, 1, 0] = 2.0 * (xy + wz)
    R[:, 1, 1] = 1.0 - 2.0 * (xx + zz)
    R[:, 1, 2] = 2.0 * (yz - wx)

    R[:, 2, 0] = 2.0 * (xz - wy)
    R[:, 2, 1] = 2.0 * (yz + wx)
    R[:, 2, 2] = 1.0 - 2.0 * (xx + yy)

    # 2. Build 4x4 Matrices
    M = np.eye(4, dtype=np.float32).reshape(1, 4, 4).repeat(N, axis=0)

    # Apply Scale & Rotation
    # M_3x3 = R * S
    # Since Scale is diagonal, we just multiply columns of R by Scale
    M[:, :3, 0] = R[:, :3, 0] * scale[:, 0, None]
    M[:, :3, 1] = R[:, :3, 1] * scale[:, 1, None]
    M[:, :3, 2] = R[:, :3, 2] * scale[:, 2, None]

    # Apply Translation
    M[:, :3, 3] = pos

    return M
