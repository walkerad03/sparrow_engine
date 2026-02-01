from dataclasses import dataclass, field

from sparrow.types import EntityId


@dataclass(frozen=True)
class ToDelete:
    entities: set[EntityId] = field(default_factory=set)


@dataclass(frozen=True)
class SimulationTime:
    # The 'real' target duration of a frame (e.g. 0.0166 for 60hz)
    fixed_delta_seconds: float = 1.0 / 60.0

    # The 'game' time passed this frame (fixed_delta * time_scale)
    # This is what systems should use for movement.
    delta_seconds: float = 1.0 / 60.0

    # Multiplier for game speed.
    # 1.0 = Normal, 0.5 = Half Speed (Slo-Mo), 0.0 = Paused
    time_scale: float = 1.0

    # Total time the game has been running (scaled)
    elapsed_seconds: float = 0.0
