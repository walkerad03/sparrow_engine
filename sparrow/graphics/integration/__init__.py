# sparrow/graphics/integration/__init__.py
from sparrow.graphics.integration.components import (
    Camera,
    DirectionalLight,
    Material,
    Mesh,
)
from sparrow.graphics.integration.extraction import extract_render_frame_system
from sparrow.graphics.integration.frame import (
    CameraData,
    ObjectInstance,
    RenderFrame,
)

__all__ = [
    "RenderFrame",
    "CameraData",
    "ObjectInstance",
    "Mesh",
    "Material",
    "Camera",
    "DirectionalLight",
    "extract_render_frame_system",
]
