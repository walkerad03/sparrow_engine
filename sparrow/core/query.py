from __future__ import annotations

from typing import Any, Generic, Iterator, Tuple, Type, TypeVar

import numpy as np

from sparrow.core.batch_view import BatchView
from sparrow.types import EntityId

T1 = TypeVar("T1")


class Query(Generic[T1]):
    def __init__(self, world: "World", *component_types: Type[Any]):
        self.world = world
        self.types = component_types

    def __iter__(
        self,
    ) -> Iterator[Tuple[EntityId, Tuple[BatchView, ...]]]:
        """
        Yields: (count, (array1, array2...))
        """
        for count, components in self.world.get_batch(*self.types):
            if count == 0:
                continue

            views = tuple(BatchView(c) for c in components)
            yield count, views

    @staticmethod
    def flat(array: np.ndarray) -> np.ndarray:
        """
        Safety Helper: Guarantees a 1D array (N,) for scalar math.
        Fixes the (N, 1) vs (N,) broadcasting crashes.
        """
        if array.ndim == 2 and array.shape[1] == 1:
            return array.ravel()
        return array

    @staticmethod
    def col(array: np.ndarray) -> np.ndarray:
        """
        Safety Helper: Guarantees a 2D Column vector (N, 1).
        Useful when writing back to a component field that expects (N, 1).
        """
        if array.ndim == 1:
            return array[:, np.newaxis]
        return array
