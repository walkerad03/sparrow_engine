import math
from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np
from numpy.typing import NDArray

from sparrow.graphics.utils.ids import MaterialId, MeshId
from sparrow.types import (
    Color,
    EntityId,
    Quaternion,
    Rect,
    Scalar,
    Vector2,
    Vector3,
)


@dataclass(frozen=True)
class EID:
    id: EntityId
    __soa_dtype__ = [("id", "i8")]


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

    __soa_dtype__ = [
        ("pos", "f4", (3,)),
        ("rot", "f4", (4,)),
        ("scale", "f4", (3,)),
    ]

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
    __soa_dtype__ = [("vec", "f4", (2,))]

    vec: Vector2


# Physics
@dataclass(frozen=True)
class RigidBody:
    __soa_dtype__ = [
        ("mass", "f4", (1,)),
        ("velocity", "f4", (3,)),
        ("inverse_mass", "f4", (1,)),
        ("angular_velocity", "f4", (3,)),
        ("inverse_inertia", "f4", (3,)),
        ("angular_drag", "f4", (1,)),
        ("restitution", "f4", (1,)),
        ("friction", "f4", (1,)),
        ("drag", "f4", (1,)),
    ]

    mass: float = 1.0
    velocity: Vector3 = field(default_factory=Vector3.zero)
    inverse_mass: float = 1.0  # 0.0 for infinite mass static objects

    angular_velocity: Vector3 = field(default_factory=Vector3.zero)
    inverse_inertia: Vector3 = field(
        default_factory=lambda: Vector3(1.0, 1.0, 1.0)
    )

    angular_drag: float = 0.0

    restitution: float = 0.5
    friction: float = 0.5
    drag: float = 0.0


@dataclass(frozen=True)
class Collider3D:
    __soa_dtype__ = [
        ("center", "f4", (3,)),
        ("size", "f4", (3,)),
    ]

    center: Vector3 = Vector3(0.0, 0.0, 0.0)
    size: Vector3 = Vector3(1.0, 1.0, 1.0)

    @property
    def half_size(self) -> Vector3:
        return self.size * 0.5


# --- GRAPHICS COMPONENTS ---


@dataclass(frozen=True)
class Sprite:
    """
    Visual representation for the Deferred Renderer.
    """

    __soa_dtype__ = [
        ("texture_id", "O"),
        ("normal_map_id", "O"),
        ("layer", "i4", (1,)),
        ("color", "f4", (4,)),
        ("region", "O"),
        ("pivot", "f4", (2,)),
    ]

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

    __soa_dtype__ = [("weight", "f4", (1,))]

    weight: float = 1.0  # How much this entity pulls the camera


# --- COLLISION COMPONENTS ---


@dataclass(frozen=True)
class BoxCollider:
    """
    Axis-Aligned Bounding Box (AABB) for physics.
    """

    __soa_dtype__ = [
        ("width", "f4", (1,)),
        ("height", "f4", (1,)),
        ("offset", "f4", (2,)),
        ("is_trigger", "?", (1,)),  # Boolean
    ]

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
    Marks this entity as a child of another.
    The HierarchySystem will snap this entity's position to the parent's.
    """

    __soa_dtype__ = [
        ("parent", "i4", (1,)),  # EntityId is an integer
        ("offset", "f4", (3,)),
    ]

    parent: EntityId
    offset: Vector3 = Vector3(0.0, 0.0, 0.0)


@dataclass
class Lifetime:
    """ """

    __soa_dtype__ = [("time_alive", "f4"), ("duration", "f4")]

    duration: Scalar  # seconds
    time_alive: Scalar = 0.0


@dataclass(frozen=True)
class Camera2D:
    __soa_dtype__ = [
        ("zoom", "f4", (1,)),  # Vertical world units visible (Ortho Scale)
        ("width", "i4", (1,)),
        ("height", "i4", (1,)),
        ("near_clip", "f4", (1,)),
        ("far_clip", "f4", (1,)),
    ]

    zoom: float = 10.0
    width: int = 1920
    height: int = 1080
    near_clip: float = -100.0
    far_clip: float = 100.0

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height


@dataclass(frozen=True)
class Camera:
    __soa_dtype__ = [
        ("fov", "f4", (1,)),
        ("width", "i4", (1,)),
        ("height", "i4", (1,)),
        ("near_clip", "f4", (1,)),
        ("far_clip", "f4", (1,)),
        ("target", "O"),  # Storing the NDArray as an object reference
    ]

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
    __soa_dtype__ = [
        ("mesh_id", "O"),
        ("material_id", "O"),
    ]

    mesh_id: MeshId
    material_id: MaterialId


@dataclass
class PointLight:
    __soa_dtype__ = [
        ("color", "f4", (3,)),
        ("intensity", "f4", (1,)),
        ("radius", "f4", (1,)),
    ]

    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    radius: float = 10.0


@dataclass
class PolygonRenderable:
    __soa_dtype__ = [
        ("vertices", "O"),
        ("color", "f4", (4,)),
        ("stroke_width", "f4", (1,)),
        ("closed", "?", (1,)),
    ]

    vertices: list[Vector2]
    color: Color
    stroke_width: Scalar
    closed: bool  # does the final point connect the first?


@dataclass
class RenderLayer:
    order: int = 0
