import math
from dataclasses import replace

import numpy as np

from sparrow.core.components import Camera, Mesh, PointLight, Transform
from sparrow.core.scene import Scene
from sparrow.core.scheduler import Stage
from sparrow.graphics.assets.material_manager import Material
from sparrow.graphics.renderer.settings import (
    ForwardRendererSettings,
    ResolutionSettings,
    SunlightSettings,
)
from sparrow.graphics.util.ids import MaterialId, MeshId
from sparrow.input.handler import InputHandler
from sparrow.resources.rendering import (
    RendererResource,
    RendererSettingsResource,
    RenderViewport,
)
from sparrow.systems.camera import camera_system
from sparrow.types import SystemId, Vector3


class SystemNames:
    CAMERA = SystemId("camera")


class TestScene(Scene):
    def on_start(self):
        self.scheduler.add_system(
            Stage.POST_UPDATE,
            camera_system,
            name=SystemNames.CAMERA,
        )

        viewport = self.world.get_resource(RenderViewport)
        w, h = viewport.width, viewport.height

        resolution = ResolutionSettings(logical_width=w, logical_height=h)
        sunlight = SunlightSettings()
        settings = ForwardRendererSettings(resolution, sunlight)
        self.world.add_resource(RendererSettingsResource(settings))

        renderer = self.world.get_resource(RendererResource).renderer
        renderer.material_manager.create(
            MaterialId("copper"),
            Material(
                base_color=(0.932, 0.623, 0.522, 1.0),
                metallic=0.5,
                roughness=0.1,
            ),
        )

        renderer.material_manager.create(
            MaterialId("bone"),
            Material(
                base_color=(0.793, 0.793, 0.664, 1.0),
                metallic=0.0,
                roughness=0.9,
            ),
        )

        x_pos = math.sin(self.frame_index + 35 / 100.0) * 4.0
        y_pos = 1.25
        z_pos = math.cos(self.frame_index / 100.0) * 4.0
        camera_pos = Vector3(x_pos, y_pos, z_pos)

        self.camera_entity = self.world.create_entity(
            Transform(pos=camera_pos),
            Camera(
                fov=70.0,
                width=w,
                height=h,
                near_clip=0.1,
                far_clip=100.0,
                target=np.array([0.0, 0.0, 0.0]),
            ),
        )

        self.world.create_entity(
            Mesh(
                mesh_id=MeshId("engine.suzanne"),
                material_id=MaterialId("copper"),
            ),
            Transform(pos=Vector3(0.0, 1.0, 0.0), scale=Vector3(1.0, 1.0, 1.0)),
        )

        self.world.create_entity(
            Mesh(
                mesh_id=MeshId("engine.large_plane"),
                material_id=MaterialId("bone"),
            ),
            Transform(pos=Vector3(0.0, 0.0, 0.0), scale=Vector3(2.5, 2.5, 2.5)),
        )

        self.world.create_entity(
            Transform(pos=Vector3(0.0, 5.0, 5.0)),
            PointLight(
                color=(0.25, 0.2, 0.2),
                intensity=500.0,
                radius=20.0,
            ),
        )

        inp = self.world.get_resource(InputHandler)
        if inp is None:
            return

        inp.set_mouse_lock(True)

        super().on_start()

    def on_update(self, dt: float):
        super().on_update(dt)

        inp = self.world.get_resource(InputHandler)
        if inp is None:
            return

        if inp.is_pressed("SPACE"):
            inp.set_mouse_lock(inp.mouse_visible)

        dx, dy = inp.get_mouse_delta()

        for eid, cam, transform in self.world.join(Camera, Transform):
            radius = math.sqrt(transform.pos.x**2 + transform.pos.z**2)
            current_angle = math.atan2(transform.pos.z, transform.pos.x)
            new_angle = current_angle + (dx * 0.05)

            new_pos = Vector3(
                math.cos(new_angle) * radius,
                transform.pos.y + dy * 0.05,
                math.sin(new_angle) * radius,
            )

            new_cam_pos = replace(transform, pos=new_pos)
            self.world.mutate_component(eid, new_cam_pos)

    def get_render_frame(self):
        return super().get_render_frame()
