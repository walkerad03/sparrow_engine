# sparrow/input/events.py
from dataclasses import dataclass


@dataclass
class KeyEvent:
    key: int
    action: int
    modifiers: int


@dataclass
class MouseMoveEvent:
    x: int
    y: int
    dx: int
    dy: int


@dataclass
class MouseClickEvent:
    x: int
    y: int
    button: int
