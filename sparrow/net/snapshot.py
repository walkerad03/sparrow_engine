from dataclasses import dataclass
from typing import List, Tuple

from sparrow.core.components import Transform


@dataclass
class WorldSnapshot:
    """
    A bundle of entity states to be sent to clients.
    """

    # List of (Entity ID, Transform State)
    entities: List[Tuple[int, Transform]]

    # Sequence number to discard old packets
    tick: int = 0
