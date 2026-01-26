# sparrow/math.py
from sparrow.types import Quaternion, Vector3


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
