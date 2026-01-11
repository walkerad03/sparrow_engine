import math
from typing import Tuple

import numpy as np

from sparrow.types import Vector3


class Camera:
    def __init__(self, resolution: Tuple[int, int]):
        self.position = np.array([0.0, 0.0], dtype="f4")
        self.target = np.array([0.0, 0.0], dtype="f4")

        self.smoothing: float = 7.5

        self.zoom = 1.0
        self.width, self.height = resolution
        self.skew_x = 0.5

        self._matrix = np.eye(4, dtype="f4")
        self._dirty = True

    def set_zoom(self, zoom: float):
        self.zoom = zoom
        self._dirty = True

    def look_at(self, x: float, y: float):
        """Sets the desired target position."""
        self.target[0] = x
        self.target[1] = y

    def update(self, dt: float):
        """Linearly interpolates position towards target."""
        # Vector math: dist = target - current
        dx = self.target[0] - self.position[0]
        dy = self.target[1] - self.position[1]

        # If we are effectively there, stop updating to save matrix math
        if abs(dx) < 1 and abs(dy) < 1:
            return

        # Apply smoothing
        # formula: current += difference * speed * dt
        self.position[0] += dx * self.smoothing * dt
        self.position[1] += dy * self.smoothing * dt
        self._dirty = True

    @property
    def matrix(self) -> bytes:
        """
        Returns the Orthographic Projection * View Matrix as bytes
        ready for ModernGL uniforms.
        """
        if self._dirty:
            self._update_matrix_perspective()
        return self._matrix.tobytes()

    def _update_matrix_perspective(self):
        fov_degrees = 60.0

        fov_rad = math.radians(fov_degrees)
        camera_height = (self.height / 2.0) / math.tan(fov_rad / 2.0)
        camera_height /= self.zoom

        z_near = 1.0
        z_far = 10000.0

        aspect = self.width / self.height
        f = 1.0 / math.tan(fov_rad / 2.0)

        proj = np.array(
            [
                [f / aspect, 0, 0, 0],
                [0, f, 0, 0],
                [0, 0, (z_far + z_near) / (z_near - z_far), -1],
                [0, 0, (2 * z_far * z_near) / (z_near - z_far), 0],
            ],
            dtype="f4",
        )

        x, y = self.position

        view = np.array(
            [
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [-x, -y, -camera_height, 1],  # <--- The Z offset is critical here
            ],
            dtype="f4",
        )

        self._matrix = np.matmul(view, proj)
        self._dirty = False

    def _update_matrix(self):
        # 1. Orthographic Projection (Left, Right, Bottom, Top, Near, Far)
        # We center 0,0 in the middle of the screen
        w = self.width / self.zoom
        h = self.height / self.zoom

        left = -w / 2
        right = w / 2
        top = h / 2
        bottom = -h / 2

        # Standard Ortho Matrix
        proj = np.array(
            [
                [2 / (right - left), 0, 0, 0],
                [0, 2 / (top - bottom), 0, 0],
                [0, 0, -1, 0],
                [
                    -(right + left) / (right - left),
                    -(top + bottom) / (top - bottom),
                    0,
                    1,
                ],
            ],
            dtype="f4",
        )

        # 2. View Matrix (Translation)
        # Moves the world opposite to the camera
        x, y = self.position
        view = np.array(
            [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [-x, -y, 0, 1]], dtype="f4"
        )

        # 3. Combine (Row-major multiplication for OpenGL)
        self._matrix = np.matmul(view, proj)
        self._dirty = False


class Camera3D:
    def __init__(self, resolution: Tuple[int, int]):
        self.width, self.height = resolution

        # Camera Configuration
        self.fov_degrees = 60.0
        self.pitch_angle = -45.0  # Degrees. -90 is Top-Down. -45 is Isometric-ish.
        self.distance = 10.0  # How far back the camera sits

        self.move_speed = 5.0  # How fast the Eye follows (Lower = Heav/Laggy)
        self.look_speed = 10.0  # How fast the Focus turns (Higher = Snappy)

        self.current_target = np.array([0.0, 0.0, 0.0], dtype="f4")
        self.current_eye = np.array([0.0, 100.0, 15.0], dtype="f4")

        self._matrix: np.ndarray | None = None
        self._dirty = True

    def update(self, dt: float, target_pos: Vector3):
        """
        Smoothly updates the camera to follow the 'target_pos' (Player).
        """
        # 1. Calculate Ideal Target (Where we WANT to look)
        # The player is on the floor (Z=0)
        ideal_target = np.array(
            [target_pos[0], target_pos[1], target_pos[2]], dtype="f4"
        )

        # 2. Calculate Ideal Eye (Where the camera SHOULD be physically)
        # Based on pitch and distance relative to the *Ideal Target*
        pitch_rad = math.radians(self.pitch_angle)

        # "North" is Y-Up in standard OpenGL logic, but your game might be Y-Down.
        # Assuming standard math:
        offset_z = abs(math.sin(pitch_rad)) * self.distance
        offset_y = math.cos(pitch_rad) * self.distance

        # The ideal eye is just the target position + the offset
        ideal_eye = ideal_target + np.array([0.0, -offset_y, offset_z], dtype="f4")

        # 3. Smoothly Interpolate (LERP)
        # a. Smoothly move the "Look At" point (Target)
        #    If look_speed is high, we focus on the player quickly.
        self.current_target += (ideal_target - self.current_target) * (
            self.look_speed * dt
        )

        # b. Smoothly move the "Physical Camera" (Eye)
        #    If move_speed is low, the camera body "drags" behind the player.
        self.current_eye += (ideal_eye - self.current_eye) * (self.move_speed * dt)

        # Mark matrix as dirty so it recalculates next time we ask for it
        self._dirty = True

    def look_at(
        self, eye: np.ndarray, target: np.ndarray, up: np.ndarray
    ) -> np.ndarray:
        f = target - eye
        f = f / np.linalg.norm(f)

        s = np.cross(f, up)
        s = s / np.linalg.norm(s)

        u = np.cross(s, f)

        # Column-vector convention, written as a row-major numpy array.
        # Translation lives in the LAST COLUMN (not last row).
        view = np.array(
            [
                [s[0], u[0], -f[0], 0.0],
                [s[1], u[1], -f[1], 0.0],
                [s[2], u[2], -f[2], 0.0],
                [-np.dot(s, eye), -np.dot(u, eye), np.dot(f, eye), 1.0],
            ],
            dtype="f4",
        )
        return view

    @property
    def numpy_matrix(self):
        """Returns the View-Projection matrix (Projection * View), transposed for GLSL."""
        if self._dirty:
            self._update_matrix()
        return self._matrix

    @property
    def matrix(self) -> bytes:
        if self._dirty:
            self._update_matrix()
        assert isinstance(self._matrix, np.ndarray)
        return self._matrix.tobytes()

    def _update_matrix(self) -> None:
        print("[DBG] eye:", self.current_eye)
        print("[DBG] target:", self.current_target)

        # 1. Projection
        fov_rad = math.radians(self.fov_degrees)
        aspect = self.width / self.height
        z_near = 0.01
        z_far = 5000.0

        f = 1.0 / math.tan(fov_rad / 2.0)

        proj = np.array(
            [
                [f / aspect, 0.0, 0.0, 0.0],
                [0.0, f, 0.0, 0.0],
                [0.0, 0.0, (z_far + z_near) / (z_near - z_far), -1.0],
                [0.0, 0.0, (2.0 * z_far * z_near) / (z_near - z_far), 0.0],
            ],
            dtype="f4",
        )

        # 2. View (Use the smoothed variables)
        up = np.array([0.0, 0.0, 1.0], dtype="f4")
        view = self.look_at(self.current_eye, self.current_target, up)

        # 3. Combine
        self._matrix = np.matmul(proj, view)
        self._dirty = False
