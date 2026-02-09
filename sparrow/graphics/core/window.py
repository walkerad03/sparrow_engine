# sparrow/graphics/core/window.py
import moderngl
import pygame

from sparrow.types import Vector2


class Window:
    """
    Manages the OS Window and OpenGL Context.
    """

    def __init__(self, width: int, height: int, title: str = "Sparrow Engine"):
        if not pygame.get_init():
            pygame.init()

        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 4)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 6)
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE
        )
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
        pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)

        self._screen = pygame.display.set_mode(
            (width, height), pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
        )
        pygame.display.set_caption(title)

        self.ctx = moderngl.create_context()
        self.ctx.enable(
            moderngl.DEPTH_TEST | moderngl.CULL_FACE | moderngl.BLEND
        )

        version = self.ctx.version_code
        print(f"OpenGL Context Created: {str(version)[0]}.{str(version)[1:]}")

    @property
    def size(self) -> Vector2:
        size = self._screen.get_size()
        return Vector2(size[0], size[1])

    def present(self) -> None:
        pygame.display.flip()

    def destroy(self) -> None:
        pygame.quit()
