import math
import random
from dataclasses import replace

import numpy as np

from sparrow.core.application import Application
from sparrow.core.components import (
    Camera,
    Collider3D,
    Mesh,
    PointLight,
    RigidBody,
    Transform,
)
from sparrow.core.scene import Scene
from sparrow.graphics.renderer.settings import (
    ForwardRendererSettings,
    ResolutionSettings,
    SunlightSettings,
)
from sparrow.graphics.utils.ids import MaterialId, MeshId
from sparrow.input.handler import InputHandler
from sparrow.resources.rendering import RendererSettingsResource, RenderViewport
from sparrow.types import Vector3


class PhysicsScene(Scene):
    spawn_cooldown = 30.0
    last_box = spawn_cooldown

    def __init__(self, app: Application):
        self.w, self.h = 1920, 1080

        resolution = ResolutionSettings(
            logical_width=self.w, logical_height=self.h
        )
        sunlight = SunlightSettings()
        self.settings = ForwardRendererSettings(resolution, sunlight)

        super().__init__(app, renderer_settings=self.settings)

    def on_start(self):
        viewport = self.world.get_resource(RenderViewport)
        w, h = viewport.width, viewport.height
        self.world.add_resource(RendererSettingsResource(self.settings))

        x_pos = math.sin(self.frame_index + 35 / 100.0) * 10.0
        y_pos = 1.25
        z_pos = math.cos(self.frame_index / 100.0) * 10.0
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
                mesh_id=MeshId("engine.plane"),
                material_id=MaterialId("engine.default"),
            ),
            Transform(
                pos=Vector3(0.0, 0.0, 0.0),
                scale=Vector3(40.0, 1.0, 40.0),
            ),
            Collider3D(size=Vector3(2.0, 0.0, 2.0)),
            RigidBody(inverse_mass=0.0, mass=0.0),
        )

        self.world.create_entity(
            Transform(pos=Vector3(0.0, 5.0, 5.0)),
            PointLight(
                color=(0.25, 0.2, 0.2),
                intensity=1.0,
                radius=20.0,
            ),
        )

        inp = self.world.get_resource(InputHandler)
        if inp is None:
            return

        inp.set_mouse_lock(True)

        super().on_start()

    def on_update(self):
        super().on_update()
        self.last_box += 1

        inp = self.world.get_resource(InputHandler)
        if inp is None:
            return

        if inp.is_pressed("SPACE") and self.last_box > self.spawn_cooldown:
            self.last_box = 0.0

            offset_amount = 0.9
            off_x = random.uniform(-offset_amount, offset_amount)
            off_z = random.uniform(-offset_amount, offset_amount)
            self.world.create_entity(
                Mesh(
                    mesh_id=MeshId("engine.cube"),
                    material_id=MaterialId("engine.default"),
                ),
                Transform(
                    pos=Vector3(off_x, 10.0, off_z),
                    scale=Vector3(0.5, 0.5, 0.5),
                ),
                RigidBody(restitution=0.1, friction=0.9),
                Collider3D(
                    center=Vector3(0.0, 0.0, 0.0),
                    size=Vector3(2.0, 2.0, 2.0),
                ),
            )

        dx, dy = inp.get_mouse_delta()
        sensitivity = 0.05

        for eid, cam, transform in self.world.join(Camera, Transform):
            pos = transform.pos

            radius = math.sqrt(pos.x**2 + pos.y**2 + pos.z**2)
            if radius < 0.01:
                radius = 15.0

            yaw = math.atan2(pos.z, pos.x)
            pitch = math.asin(max(-1.0, min(1.0, pos.y / radius)))

            yaw += dx * sensitivity
            pitch += dy * sensitivity

            pitch_limit = 1.55
            pitch = max(-pitch_limit, min(pitch_limit, pitch))

            new_y = radius * math.sin(pitch)
            h_radius = radius * math.cos(pitch)
            new_x = h_radius * math.cos(yaw)
            new_z = h_radius * math.sin(yaw)

            new_pos = Vector3(new_x, new_y, new_z)
            self.world.mutate_component(eid, replace(transform, pos=new_pos))

    def get_render_frame(self):
        return super().get_render_frame()
