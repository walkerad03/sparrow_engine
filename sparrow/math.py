from sparrow.types import Quaternion, Vector3


def cross_product_vec3(a: Vector3, b: Vector3) -> Vector3:
    return Vector3(
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    )


def mul_quat(q1: Quaternion, q2: Quaternion) -> Quaternion:
    """Multiply two quaternions (q1 * q2)."""
    return Quaternion(
        x=q1.w * q2.x + q1.x * q2.w + q1.y * q2.z - q1.z * q2.y,
        y=q1.w * q2.y - q1.x * q2.z + q1.y * q2.w + q1.z * q2.x,
        z=q1.w * q2.z + q1.x * q2.y - q1.y * q2.x + q1.z * q2.w,
        w=q1.w * q2.w - q1.x * q2.x - q1.y * q2.y - q1.z * q2.z,
    )
