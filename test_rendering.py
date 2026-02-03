import sys
from pathlib import Path

import pygame

from sparrow.assets import AssetServer, DefaultMeshes
from sparrow.core.components import Transform
from sparrow.core.query import Query
from sparrow.core.world import World
from sparrow.graphics.core import Renderer, RendererSettings, Window
from sparrow.graphics.integration.components import (
    Camera,
    DirectionalLight,
    Material,
    Mesh,
)
from sparrow.graphics.integration.extraction import extract_render_frame_system
from sparrow.graphics.integration.frame import RenderFrame
from sparrow.graphics.pipelines.standard_3d import build_standard_3d_pipeline
from sparrow.resources.core import SimulationTime
from sparrow.types import Quaternion, Vector3


def main():
    window = Window(
        width=1920, height=1080, title="Sparrow Engine - New Architecture"
    )

    asset_server = AssetServer(asset_root=Path(".") / "sparrow" / "assets")

    renderer = Renderer(ctx=window.ctx, asset_server=asset_server)
    renderer.set_pipeline(build_standard_3d_pipeline)

    world = World()
    world.add_resource(RendererSettings())
    world.add_resource(SimulationTime())

    print("Loading Assets...")
    cube_handle = asset_server.load(DefaultMeshes.CUBE)

    world.create_entity(
        Transform(pos=Vector3(0, 0, 0)),
        Mesh(handle=cube_handle),
        Material(base_color=(1.0, 0.5, 0.2, 1.0)),  # Orange
    )

    world.create_entity(
        Transform(
            pos=Vector3(0, 2, 9),
            rot=Quaternion(0, 0, 0, 1),
        ),  # TODO: LookAt rotation math
        Camera(fov=60.0, near=0.1, far=100.0, active=True),
    )

    world.create_entity(
        Transform(), DirectionalLight(color=(1.0, 0.9, 0.8), intensity=1.5)
    )

    running = True
    clock = pygame.time.Clock()

    print("Starting Loop...")

    t = 0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        t += 1 / 60
        for count, (trans_view, mesh_view) in Query(world, Transform, Mesh):
            new_rot = Quaternion.from_euler(0, t, 0)
            trans_view.rot[:] = new_rot

        extract_render_frame_system(world)

        frame = world.try_resource(RenderFrame)
        if frame:
            renderer.render(frame)

        window.present()
        clock.tick(60)

    window.destroy()
    sys.exit()


if __name__ == "__main__":
    main()
