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
                metalness=1.0,
                roughness=0.9,
            ),
        )

        w, h = self.app.screen_size

        self.camera_entity = self.world.create_entity(
            Transform(pos=Vector3(1, 1, -2)),
            Camera(
                fov=60.0,
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
            Transform(pos=Vector3(0.0, 1.0, 0.0)),
        )

        self.world.create_entity(
            Mesh(
                mesh_id=MeshId("engine.large_plane"),
                material_id=MaterialId("bone"),
            ),
            Transform(pos=Vector3(0.0, 0.0, 0.0)),
        )

    def on_update(self, dt: float):
        super().on_update(dt)

        x_pos = math.sin(self.frame_index / 100.0) * 4.0
        y_pos = 1.25
        z_pos = math.cos(self.frame_index / 100.0) * 4.0

        for eid, transform, camera in self.world.join(Transform, Camera):
            new_t = replace(transform, pos=Vector3(x_pos, y_pos, z_pos))
            self.world.mutate_component(eid, new_t)

    def get_render_frame(self):
        return super().get_render_frame()


@profile(out_dir=Path(".debug"), enabled=True)
def main() -> None:
    """Main entrypoint for the minimal renderer test app."""
    app = Application(width=192, height=108)
    app.run(PrimaryScene)


if __name__ == "__main__":
    main()
