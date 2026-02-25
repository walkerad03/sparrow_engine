from dataclasses import dataclass


@dataclass
class SimulationTime:
    fixed_dt: float
    ticks: int = 0
