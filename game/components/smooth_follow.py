from dataclasses import dataclass

from sparrow.types import EntityId, Vector3


@dataclass
class SmoothFollow:
    """
    Component: Entity will float towards the target using interpolation.
    """

    target: EntityId
    offset_x: float = 0.0
    offset_y: float = 0.0
    offset_z: float = 0.0
    speed: float = 5.0  # Higher = Snappier, Lower = Floaty

    wander_radius: float = 0.0
    wander_interval: float = 2.0

    _timer: float = 0.0
    _current_wander: Vector3 = (0.0, 0.0, 0.0)
