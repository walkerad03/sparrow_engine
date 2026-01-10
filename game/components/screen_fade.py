from dataclasses import dataclass


@dataclass
class ScreenFade:
    """
    Component: Controls the alpha transparency of an entity over time.
    """

    duration: float
    timer: float = 0.0
    fade_type: str = "in"  # "in" = Black -> Transparent, "out" = Transparent -> Black
