# sparrow/assets/defaults/__init__.py
from enum import StrEnum


class DefaultMeshes(StrEnum):
    CUBE = "defaults/meshes/cube.obj"
    SPHERE = "defaults/meshes/dense_icosphere.obj"
    PLANE = "defaults/meshes/plane.obj"
    BUNNY = "defaults/meshes/stanford-bunny.obj"
    SUZANNE = "defaults/meshes/suzanne.obj"
    DRAGON = "defaults/meshes/xyzrgb_dragon.obj"
    DRAGON_DECIMATED = "defaults/meshes/xyzrgb_dragon_decimated.obj"


class DefaultTextures(StrEnum):
    SPLASH = "defaults/textures/splashscreen.png"


class DefaultShaders(StrEnum):
    FORWARD_VS = "defaults/shaders/forward.vert"
    FORWARD_FS = "defaults/shaders/forward.frag"


__all__ = [
    "DefaultMeshes",
    "DefaultTextures",
    "DefaultShaders",
]
