# main.py

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import numpy as np

from sparrow.core.application import Application
from sparrow.core.components import Camera, Mesh, Transform
from sparrow.core.scene import Scene
from sparrow.graphics.assets.material_manager import Material
from sparrow.graphics.debug.profiler import profile
from sparrow.graphics.util.ids import MaterialId, MeshId
from sparrow.input.handler import InputHandler
from sparrow.types import Vector3


class PrimaryScene(Scene):
    def on_start(self):
        self.app.renderer.material_manager.create(
            MaterialId("copper"),
            Material(
                base_color_factor=(0.932, 0.623, 0.522, 1.0),
                metalness=1.0,
                roughness=0.0,
            ),
        )

        self.app.renderer.material_manager.create(
            MaterialId("bone"),
            Material(
                base_color_factor=(0.793, 0.793, 0.664, 1.0),
                metalness=0.0,
                roughness=0.9,
            ),
        )

        w, h = self.app.screen_size

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
                mesh_id=MeshId("engine.stanford_dragon_lowpoly"),
                material_id=MaterialId("copper"),
            ),
            Transform(pos=Vector3(0.0, 0.0, 0.0), scale=Vector3(2.5, 2.5, 2.5)),
        )

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


@profile(out_dir=Path(".debug"), enabled=True)
def main() -> None:
    """Main entrypoint for the minimal renderer test app."""
    app = Application(width=1920, height=1080)
    app.run(PrimaryScene)


if __name__ == "__main__":
    main()
