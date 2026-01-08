from dataclasses import dataclass

import pytest

from sparrow.core.world import World


@dataclass(frozen=True)
class Position:
    x: float
    y: float


@dataclass(frozen=True)
class Velocity:
    x: float
    y: float


@dataclass(frozen=True)
class Health:
    hp: int


@pytest.fixture
def world():
    """Returns a fresh World instance for each test."""
    return World()
