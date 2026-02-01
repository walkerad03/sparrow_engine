from dataclasses import dataclass


@dataclass(frozen=True)
class Boid:
    __soa_dtype__ = [
        ("separation_weight", "f4"),
        ("alignment_weight", "f4"),
        ("cohesion_weight", "f4"),
        ("target_weight", "f4"),
        ("visual_range", "f4"),
        ("protected_range", "f4"),
    ]
    separation_weight: float = 1.5
    alignment_weight: float = 1.0
    cohesion_weight: float = 1.0
    target_weight: float = 0.5
    visual_range: float = 150.0
    protected_range: float = 30.0
