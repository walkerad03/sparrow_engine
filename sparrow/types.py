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

Number: TypeAlias = float


@dataclass(frozen=True, slots=True)
class Vector2:
    x: Number
    y: Number

    @staticmethod
    def zero() -> Vector2:
        return Vector2(0.0, 0.0)

    def __iter__(self) -> Iterator[Number]:
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
    def __getitem__(self, index: int) -> Number: ...
    @overload
    def __getitem__(self, index: slice) -> tuple[Number, ...]: ...

    def __getitem__(self, index: Any):
        if isinstance(index, int):
            if index == 0:
                return self.x
            if index == 1:
                return self.y
            raise IndexError(index)

        if isinstance(index, slice):
            return tuple(self)[index]

        raise TypeError(f"indices must be int or slice, not {type(index).__name__}")


@dataclass(frozen=True, slots=True)
class Vector3:
    x: Number
    y: Number
    z: Number

    @staticmethod
    def zero() -> Vector3:
        return Vector3(0.0, 0.0, 0.0)

    def __iter__(self) -> Iterator[Number]:
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
    def __getitem__(self, index: int) -> Number: ...
    @overload
    def __getitem__(self, index: slice) -> tuple[Number, ...]: ...

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

        raise TypeError(f"indices must be int or slice, not {type(index).__name__}")


@dataclass(frozen=True, slots=True)
class Quaternion:
    x: Number
    y: Number
    z: Number
    w: Number

    def __iter__(self) -> Iterator[Number]:
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
            self.x * self.x + self.y * self.y + self.z * self.z + self.w * self.w
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
            dtype=np.float32,
        )
