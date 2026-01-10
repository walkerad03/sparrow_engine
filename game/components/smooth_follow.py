from dataclasses import dataclass

from sparrow.types import EntityId, Vector2


@dataclass
class SmoothFollow:
    """
    Component: Entity will float towards the target using interpolation.
    """

    target: EntityId
    offset_x: float = 0.0
    offset_y: float = 0.0
    speed: float = 5.0  # Higher = Snappier, Lower = Floaty

    wander_radius: float = 0.0
    wander_interval: float = 2.0

    _timer: float = 0.0
    _current_wander: Vector2 = (0.0, 0.0)

    @classmethod
    def get_timer(cls) -> float:
        return cls._timer

    @classmethod
    def get_current_wander(cls) -> Vector2:
        return cls._current_wander
