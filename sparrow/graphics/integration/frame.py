from dataclasses import dataclass, field
from typing import List

import numpy as np

from sparrow.assets.handle import AssetId
from sparrow.types import Color3, Color4, EntityId, Scalar, Vector3


@dataclass(slots=True)
class CameraData:
    view: np.ndarray  # 4x4
    proj: np.ndarray  # 4x4
    view_proj: np.ndarray  # 4x4
    position: np.ndarray  # 3 (vec3)
    near: Scalar
    far: Scalar


@dataclass(slots=True)
class ObjectInstance:
    """
    A single renderable object extracted from the world.
    """

    entity_id: EntityId
    mesh_id: AssetId
    transform_index: int  # Index into RenderFrame.transforms
    # Material data could be an ID or direct properties
    albedo_id: AssetId | None
    color: Color4
    roughness: Scalar
    metallic: Scalar


@dataclass(slots=True)
class RenderFrame:
    """
    Snapshot of the game state for a single frame.
    """

    camera: CameraData

    # Flattened lists for iteration
    objects: List[ObjectInstance] = field(default_factory=list)
    transforms: np.ndarray = field(
        default_factory=lambda: np.zeros((0, 4, 4), dtype="f4")
    )

    # Lighting info
    sun_direction: Vector3 = Vector3(0.0, -1.0, 0.0)
    sun_color: Color3 = (1.0, 1.0, 1.0)

    # Time
    time: float = 0.0
    delta_time: float = 0.0
    frame_index: int = 0
