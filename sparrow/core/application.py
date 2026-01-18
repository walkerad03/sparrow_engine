# sparrow/core/application.py
import time
from typing import Optional, Type

import moderngl
import pygame

from sparrow.core.scene import Scene
from sparrow.input.handler import InputHandler
from sparrow.resources.rendering import RenderContext, RenderViewport


class Application:
    def __init__(self, width: int = 1280, height: int = 720, title: str = "Sparrow"):
        self.screen_size = (width, height)
        self.window: pygame.Surface | None = None
        self.ctx: moderngl.Context | None = None
        self._title = title
        self.clock: pygame.time.Clock | None = None
        self._pygame_initialized = False
        self.running = False
        self.active_scene: Optional[Scene] = None

    def _ensure_window(self) -> None:
        if self.window is not None:
            return

        pygame.init()
        self._pygame_initialized = True

        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 4)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 6)
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE
        )
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)

        self.window = pygame.display.set_mode(
            self.screen_size, pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
        )
        pygame.display.set_caption(self._title)

        self.ctx = moderngl.create_context(460)
        gl_version = self.ctx.version_code
        print(f"OpenGL version {str(gl_version)[0]}.{str(gl_version)[1:]}")
        self.ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)

        self.clock = pygame.time.Clock()

    def run(self, start_scene_cls: Type[Scene]) -> None:
        self.change_scene(start_scene_cls)
        self.running = True

        while self.running:
            if self.window is not None:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.running = False

                    if self.active_scene:
                        inp = self.active_scene.world.get_resource(InputHandler)
                        inp.process_event(event)

            if self.active_scene:
                now = time.perf_counter()
                dt = now - self.active_scene.last_time
                self.active_scene.last_time = now

                self.active_scene.on_update(dt)
                self.active_scene.on_render()

            if self.window is not None:
                pygame.display.flip()

            if self.clock is not None:
                self.clock.tick(60)
            else:
                time.sleep(1 / 60)

        if self._pygame_initialized:
            pygame.quit()

    def change_scene(self, scene_cls: Type[Scene]) -> None:
        if self.active_scene:
            self.active_scene.on_exit()

        self.active_scene = scene_cls(self)
        if self.active_scene.render_enabled:
            self._ensure_window()
            assert self.ctx is not None
            w, h = self.screen_size
            self.active_scene.world.add_resource(RenderViewport(width=w, height=h))
            self.active_scene.world.add_resource(RenderContext(gl=self.ctx))
            self.active_scene.configure_rendering()
        self.active_scene.on_start()
