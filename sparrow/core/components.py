import math
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

from sparrow.graphics.util.ids import MaterialId, MeshId
from sparrow.types import EntityId, Quaternion, Rect, Vector2, Vector3

# --- SPATIAL COMPONENTS ---


def transform_to_matrix(
    position: Vector3,
    rotation: Quaternion,
    scale: Vector3,
) -> np.ndarray:
    T = np.eye(4, dtype=np.float64)
    T[0:3, 3] = [position.x, position.y, position.z]
    R = rotation.to_matrix4()

    S = np.eye(4, dtype=np.float64)
    S[0, 0] = scale.x
    S[1, 1] = scale.y
    S[2, 2] = scale.z

    # Calculate standard matrix
    model = T @ R @ S

    return model


@dataclass(frozen=True)
class Transform:
    """
    The physical location of an entity in the world.
    """

    pos: Vector3 = Vector3(0.0, 0.0, 0.0)
    rot: Quaternion = Quaternion.identity()
    scale: Vector3 = Vector3(1.0, 1.0, 1.0)

    @property
    def matrix_transform(self) -> NDArray[np.float64]:
        return transform_to_matrix(
            self.pos,
            self.rot,
            self.scale,
        )


@dataclass(frozen=True)
class Velocity:
    """
    Rate of change for the Transform.
    Used by the Physics/Movement System.
    """

    x: float = 0.0
    y: float = 0.0
    damping: float = 0.9  # Friction (0.0 = stops instantly, 1.0 = no friction)


# --- GRAPHICS COMPONENTS ---


@dataclass(frozen=True)
class Sprite:
    """
    Visual representation for the Deferred Renderer.
    """

    texture_id: str  # Key for the Texture Atlas
    normal_map_id: Optional[str] = None
    layer: int = 0  # Z-Index (0 = Floor, 1 = Items, 2 = Actors)
    color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)  # Tint

    # Texture region (u, v, w, h) in normalized coordinates (0.0 to 1.0)
    # Default is full texture
    region: Optional[Rect] = None

    # Pivot point for rotation (0.5, 0.5 is center)
    pivot: Vector2 = Vector2(0.5, 0.5)


@dataclass(frozen=True)
class CameraTarget:
    """
    Tag Component.
    The Camera System will smooth-follow the average position of all entities with this tag.
    """

    weight: float = 1.0  # How much this entity pulls the camera


# --- COLLISION COMPONENTS ---


@dataclass(frozen=True)
class BoxCollider:
    """
    Axis-Aligned Bounding Box (AABB) for physics.
    """

    width: float
    height: float
    offset: Vector2 = Vector2(0.0, 0.0)
    is_trigger: bool = (
        False  # If True, detects overlap but doesn't block movement
    )

    @property
    def bounds(self) -> Rect:
        """Returns local bounds (x, y, w, h). Needs Transform to get World bounds."""
        return (self.offset[0], self.offset[1], self.width, self.height)


@dataclass
class ChildOf:
    """
    Component: Marks this entity as a child of another.
    The HierarchySystem will snap this entity's position to the parent's.
    """

    parent: EntityId
    offset: Vector2 = Vector2(0.0, 0.0)


@dataclass(frozen=True)
class Camera:
    fov: float
    width: int
    height: int
    near_clip: float
    far_clip: float

    target: NDArray[np.float64]

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height

    @property
    def projection_matrix(self) -> NDArray[np.float64]:
        """
        Calculates the infinite perspective projection matrix.
        Cached property logic could be added here if this becomes a bottleneck.
        """
        aspect = self.aspect_ratio
        tan_half_fov = math.tan(math.radians(self.fov) * 0.5)
        fl = 1.0 / tan_half_fov

        inv_nf = 1.0 / (self.near_clip - self.far_clip)
        p22 = (self.far_clip + self.near_clip) * inv_nf
        p23 = (2.0 * self.far_clip * self.near_clip) * inv_nf

        return np.array(
            [
                [fl / aspect, 0.0, 0.0, 0.0],
                [0.0, fl, 0.0, 0.0],
                [0.0, 0.0, p22, p23],
                [0.0, 0.0, -1.0, 0.0],
            ],
            dtype=np.float64,
        )


@dataclass
class Mesh:
    mesh_id: MeshId
    material_id: MaterialId


@dataclass
class RenderSettings:
    pipeline: Literal["deferred", "forward"] = "deferred"
    enable_bloom: bool = True
    enable_ssao: bool = False
    enable_chromatic: bool = False


@dataclass
class PointLight:
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    radius: float = 10.0
