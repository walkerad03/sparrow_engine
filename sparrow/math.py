# sparrow/math.py
import math
from typing import TypeVar, Union

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
