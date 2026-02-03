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


def quaternion_to_matrix(q: Union[Quaternion, np.ndarray, list]) -> np.ndarray:
    """
    Converts a single quaternion into a 4x4 Rotation Matrix.
    q: Quaternion object (x,y,z,w) or array-like [x,y,z,w].
    """
    if hasattr(q, "x"):
        x, y, z, w = q.x, q.y, q.z, q.w
    else:
        x, y, z, w = q[0], q[1], q[2], q[3]

    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z

    mat = np.eye(4, dtype=np.float32)

    mat[0, 0] = 1.0 - 2.0 * (yy + zz)
    mat[0, 1] = 2.0 * (xy - wz)
    mat[0, 2] = 2.0 * (xz + wy)

    mat[1, 0] = 2.0 * (xy + wz)
    mat[1, 1] = 1.0 - 2.0 * (xx + zz)
    mat[1, 2] = 2.0 * (yz - wx)

    mat[2, 0] = 2.0 * (xz - wy)
    mat[2, 1] = 2.0 * (yz + wx)
    mat[2, 2] = 1.0 - 2.0 * (xx + yy)

    return mat


def create_view_matrix(
    pos: Union[Vector3, np.ndarray], rot: Union[Quaternion, np.ndarray]
) -> np.ndarray:
    """
    Constructs a View Matrix (World -> Camera Space)  from a position and rotation.
    This effectively applies the inverse of the Camera's Model Matrix.
    """
    # 1. Get Rotation Matrix (Camera -> World orientation)
    R = quaternion_to_matrix(rot)

    # 2. Transpose R to get Inverse Rotation (World -> Camera)
    # (Since rotation matrices are orthogonal, R^-1 == R.T)
    R_inv = R.T

    # 3. Create Inverse Translation Matrix (Move world by -pos)
    T_inv = np.eye(4, dtype=np.float32)
    T_inv[:3, 3] = -np.array(pos, dtype=np.float32)

    # 4. View = R_inv * T_inv
    # We apply translation first (relative to world), then rotation.
    # Mathematically: (T * R)^-1 = R^-1 * T^-1
    return R_inv @ T_inv


def create_perspective_projection(
    fov_deg: float, aspect: float, near: float, far: float
) -> np.ndarray:
    """
    Creates a standard OpenGL Perspective Projection Matrix.
    fov_deg: Field of View in Degrees (Vertical)
    aspect: Width / Height
    near: Distance to near plane
    far: Distance to far plane
    """
    fov_rad = math.radians(fov_deg)
    tan_half_fov = math.tan(fov_rad / 2.0)

    # Avoid division by zero
    if tan_half_fov == 0:
        tan_half_fov = 0.001
    if near == far:
        far += 0.001
    if aspect == 0:
        aspect = 1.0

    mat = np.zeros((4, 4), dtype=np.float32)

    # Scale X (Width)
    mat[0, 0] = 1.0 / (aspect * tan_half_fov)

    # Scale Y (Height)
    mat[1, 1] = 1.0 / tan_half_fov

    # Remap Z (Depth)
    mat[2, 2] = (far + near) / (near - far)
    mat[2, 3] = (2.0 * far * near) / (near - far)

    # Perspective Division (w = -z)
    mat[3, 2] = -1.0

    return mat
