from typing import Tuple

import numpy as np


class Camera:
    def __init__(self, resolution: Tuple[int, int]):
        self.position = np.array([0.0, 0.0], dtype="f4")
        self.target = np.array([0.0, 0.0], dtype="f4")

        self.smoothing: float = 5.0

        self.zoom = 1.0
        self.width, self.height = resolution

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
        if abs(dx) < 0.1 and abs(dy) < 0.1:
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
            self._update_matrix()
        return self._matrix.tobytes()

    def _update_matrix(self):
        # 1. Orthographic Projection (Left, Right, Bottom, Top, Near, Far)
        # We center 0,0 in the middle of the screen
        left = -self.width / 2 / self.zoom
        right = self.width / 2 / self.zoom
        bottom = -self.height / 2 / self.zoom
        top = self.height / 2 / self.zoom

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
