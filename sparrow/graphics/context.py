import array
from typing import Tuple

import moderngl
import pygame


class GraphicsContext:
    def __init__(self, resolution: Tuple[int, int], scale: int = 3):
        """
        Initializes the Window and OpenGL Context.

        :param resolution: The native logic resolution (e.g., 480x270)
        :param scale: Integer scaling factor for the window (e.g., x3 = 1440x810)
        """

        self.logical_res = resolution
        self.window_res = (resolution[0] * scale, resolution[1] * scale)

        pygame.init()
        pygame.display.set_mode(self.window_res, pygame.OPENGL | pygame.DOUBLEBUF)

        self.ctx = moderngl.create_context()

        self.ctx.enable(moderngl.BLEND | moderngl.DEPTH_TEST)

        quad_data = array.array(
            "f",
            [
                -1.0,
                1.0,
                0.0,
                1.0,
                -1.0,
                -1.0,
                0.0,
                0.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                -1.0,
                1.0,
                0.0,
            ],
        )

        self.quad_buffer = self.ctx.buffer(data=quad_data.tobytes())

    def clear(self):
        self.ctx.clear(0, 0, 0)

    def flip(self):
        pygame.display.flip()

    @property
    def dt(self) -> float:
        """Placeholder for actual clock data"""
        return 1 / 30
