from dataclasses import dataclass
from typing import Optional, Tuple

from ..types import EntityId, Rect, Vector2

# --- SPATIAL COMPONENTS ---


@dataclass(frozen=True)
class Transform:
    """
    The physical location of an entity in the world.
    """

    x: float
    y: float
    rotation: float = 0.0  # Radians
    scale: Vector2 = (1.0, 1.0)

    @property
    def pos(self) -> Vector2:
        return (self.x, self.y)


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
    pivot: Vector2 = (0.5, 0.5)
    skew: float = 0.0


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
    offset: Vector2 = (0.0, 0.0)
    is_trigger: bool = False  # If True, detects overlap but doesn't block movement

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
    offset: Vector2 = (0.0, 0.0)
