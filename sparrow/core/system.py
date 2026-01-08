from __future__ import annotations

from sparrow.core.world import World


class System:
    """
    Base class for all Logic Systems.
    """

    def process(self, world: World) -> None:
        raise NotImplementedError
