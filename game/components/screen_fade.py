from dataclasses import dataclass

from sparrow.core.component import Component


@dataclass
class ScreenFade(Component):
    """
    Component: Controls the alpha transparency of an entity over time.
    """

    duration: float
    timer: float = 0.0
    fade_type: str = "in"  # "in" = Black -> Transparent, "out" = Transparent -> Black
