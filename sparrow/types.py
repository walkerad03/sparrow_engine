# sparrow/types.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterator, NewType, Tuple, TypeAlias, overload

import numpy as np

EntityId = NewType("EntityId", int)
ArchetypeMask = NewType("ArchetypeMask", int)
SystemId = NewType("SystemId", str)

Rect = Tuple[float, float, float, float]  # x, y, w, h

InputAction = str

Address = Tuple[str, int]

Scalar: TypeAlias = float


@dataclass(frozen=True, slots=True)
class Vector2:
    x: Scalar
    y: Scalar

    @staticmethod
    def zero() -> Vector2:
        return Vector2(0.0, 0.0)

    def __iter__(self) -> Iterator[Scalar]:
        yield self.x
        yield self.y

    def __len__(self) -> int:
        return 2

    def __add__(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    @overload
    def __truediv__(self, other: float) -> Vector2: ...
    @overload
    def __truediv__(self, other: Vector2) -> Vector2: ...

    def __truediv__(self, other: Any):
        if isinstance(other, float):
            if other == 0.0:
                raise ValueError(other)
            return Vector2(self.x / other, self.y / other)

        if isinstance(other, Vector2):
            if other.x == 0 or other.y == 0:
                raise ValueError(other)
            return Vector2(self.x / other.x, self.y / other.y)

        raise TypeError(
            f"other must be Vector2 or Scalar, not {type(other).__name__}"
        )

    @overload
    def __getitem__(self, index: int) -> Scalar: ...
    @overload
    def __getitem__(self, index: slice) -> tuple[Scalar, ...]: ...

    def __getitem__(self, index: Any):
        if isinstance(index, int):
            if index == 0:
                return self.x
            if index == 1:
                return self.y
            raise IndexError(index)

        if isinstance(index, slice):
            return tuple(self)[index]

        raise TypeError(
            f"indices must be int or slice, not {type(index).__name__}"
        )


@dataclass(frozen=True, slots=True)
class Vector3:
    x: Scalar
    y: Scalar
    z: Scalar

    @staticmethod
    def zero() -> Vector3:
        return Vector3(0.0, 0.0, 0.0)

    def __iter__(self) -> Iterator[Scalar]:
        yield self.x
        yield self.y
        yield self.z

    def __len__(self) -> int:
        return 3

    def __add__(self, other: Vector3) -> Vector3:
        return Vector3(
            self.x + other.x,
            self.y + other.y,
            self.z + other.z,
        )

    def __sub__(self, other: Vector3) -> Vector3:
        return Vector3(
            self.x - other.x,
            self.y - other.y,
            self.z - other.z,
        )

    def __mul__(self, scalar: float) -> Vector3:
        return Vector3(
            self.x * scalar,
            self.y * scalar,
            self.z * scalar,
        )

    @overload
    def __truediv__(self, other: float) -> Vector3: ...
    @overload
    def __truediv__(self, other: Vector3) -> Vector3: ...

    def __truediv__(self, other: Any):
        if isinstance(other, float):
            if other == 0.0:
                raise ValueError(other)
            return Vector3(self.x / other, self.y / other, self.z / other)

        if isinstance(other, Vector3):
            if other.x == 0 or other.y == 0:
                raise ValueError(other)
            return Vector3(self.x / other.x, self.y / other.y, self.z / other.z)

        raise TypeError(
            f"other must be Vector3 or Scalar, not {type(other).__name__}"
        )

    @overload
    def __getitem__(self, index: int) -> Scalar: ...
    @overload
    def __getitem__(self, index: slice) -> tuple[Scalar, ...]: ...

    def __getitem__(self, index: Any):
        if isinstance(index, int):
            if index == 0:
                return self.x
            if index == 1:
                return self.y
            if index == 2:
                return self.z
            raise IndexError(index)

        if isinstance(index, slice):
            return tuple(self)[index]

        raise TypeError(
            f"indices must be int or slice, not {type(index).__name__}"
        )


@dataclass(frozen=True, slots=True)
class Quaternion:
    x: Scalar
    y: Scalar
    z: Scalar
    w: Scalar

    def __iter__(self) -> Iterator[Scalar]:
        yield self.x
        yield self.y
        yield self.z
        yield self.w

    @staticmethod
    def identity() -> Quaternion:
        return Quaternion(0.0, 0.0, 0.0, 1.0)

    @staticmethod
    def from_euler(pitch: float, yaw: float, roll: float) -> Quaternion:
        """
        Euler angles in radians.
        pitch = rotation about X
        yaw   = rotation about Y
        roll  = rotation about Z
        """
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)

        return Quaternion(
            x=sr * cp * cy - cr * sp * sy,
            y=cr * sp * cy + sr * cp * sy,
            z=cr * cp * sy - sr * sp * cy,
            w=cr * cp * cy + sr * sp * sy,
        )

    def normalized(self) -> Quaternion:
        n = (
            self.x * self.x
            + self.y * self.y
            + self.z * self.z
            + self.w * self.w
        ) ** 0.5
        if n == 0.0:
            return Quaternion(0.0, 0.0, 0.0, 1.0)
        inv = 1.0 / n
        return Quaternion(
            self.x * inv,
            self.y * inv,
            self.z * inv,
            self.w * inv,
        )

    def to_matrix4(self) -> np.ndarray:
        """
        Convert quaternion to a 4x4 column-major rotation matrix.
        """
        q = self.normalized()

        x = q.x
        y = q.y
        z = q.z
        w = q.w

        xx = x * x
        yy = y * y
        zz = z * z
        xy = x * y
        xz = x * z
        yz = y * z
        wx = w * x
        wy = w * y
        wz = w * z

        # Column-major 4x4 rotation matrix
        return np.array(
            [
                [1.0 - 2.0 * (yy + zz), 2.0 * (xy - wz), 2.0 * (xz + wy), 0.0],
                [2.0 * (xy + wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz - wx), 0.0],
                [2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (xx + yy), 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )


@dataclass
class Rectangle:
    x: Scalar
    y: Scalar
    width: Scalar
    height: Scalar


@dataclass
class BoundingBox3D:
    min: Vector3
    max: Vector3


@dataclass
class BoundingBox2D:
    min: Vector2
    max: Vector2


@dataclass
class Ray3D:
    position: Vector3
    direction: Vector3


@dataclass
class Ray2D:
    position: Vector2
    direction: Vector2


@dataclass
class RayCollision2D:
    hit: bool
    distance: float
    point: Vector2
    normal: Vector2
