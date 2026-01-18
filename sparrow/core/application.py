# sparrow/core/application.py
import time
from typing import Optional, Type

import moderngl
import pygame

from sparrow.core.scene import Scene
from sparrow.graphics.renderer.renderer import Renderer
from sparrow.graphics.renderer.settings import (
    DeferredRendererSettings,
    PresentScaleMode,
    ResolutionSettings,
    SunlightSettings,
)
from sparrow.input.handler import InputHandler


class Application:
    def __init__(self, width: int = 1280, height: int = 720, title: str = "Sparrow"):
        pygame.init()

        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 4)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 6)
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE
        )
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)

        self.screen_size = (width, height)
        self.window = pygame.display.set_mode(
            self.screen_size, pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
        )
        pygame.display.set_caption(title)

        self.ctx = moderngl.create_context(460)
        gl_version = self.ctx.version_code
        print(f"OpenGL version {str(gl_version)[0]}.{str(gl_version)[1:]}")
        self.ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)

        resolution = ResolutionSettings(
            logical_width=int(width / 1),
            logical_height=int(height / 1),
            scale_mode=PresentScaleMode.INTEGER_FIT,
        )

        sunlight = SunlightSettings()

        self.renderer = Renderer(
            self.ctx,
            DeferredRendererSettings(resolution, sunlight),
        )
        self.renderer.initialize()

        self.input = InputHandler()
        self.clock = pygame.Clock()
        self.running = False
        self.active_scene: Optional[Scene] = None

    def run(self, start_scene_cls: Type[Scene]) -> None:
        self.change_scene(start_scene_cls)
        self.running = True

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

                self.input.process_event(event)

            if self.active_scene:
                now = time.perf_counter()
                dt = now - self.active_scene.last_time
                self.active_scene.last_time = now

                self.active_scene.on_update(dt)

                frame = self.active_scene.get_render_frame()

                self.renderer.render_frame(frame)

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()

    def change_scene(self, scene_cls: Type[Scene]) -> None:
        if self.active_scene:
            self.active_scene.on_exit()

        self.active_scene = scene_cls(self)
        self.active_scene.on_start()
