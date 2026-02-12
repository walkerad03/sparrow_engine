import numpy as np


class ArrayView:
    __slots__ = ("_data",)

    def __init__(self, data: np.ndarray):
        self._data = data

    def col(self, index: int):
        """Accesses a specific column (e.g., X or Y) as a new view."""
        return ArrayView(self._data[:, index])

    def __add__(self, other):
        val = other._data if isinstance(other, ArrayView) else other
        return ArrayView(self._data + val)

    def __iadd__(self, other):
        val = other._data if isinstance(other, ArrayView) else other
        self._data += val
        return self

    def __mul__(self, other):
        val = other._data if isinstance(other, ArrayView) else other
        return ArrayView(self._data * val)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __radd__(self, other):
        return self.__add__(other)

    def __getitem__(self, key):
        return ArrayView(self._data[key])


class VectorView:
    """
    A mutable view into the columns of a Structured Array.
    This acts like a Vector2/3 but modifies the raw memory in-place.
    """

    __slots__ = ("_data", "_col_idx")

    def __init__(self, data: np.ndarray):
        # data is the view into the specific field (e.g. 'pos')
        # shape is (N, 2) or (N, 3)
        self._data = data

    @property
    def vec(self) -> np.ndarray:
        """Returns the raw (N, 2) or (N, 3) NumPy array."""
        return self._data

    def __getitem__(self, key):
        """Allows access like polys.color[i]"""
        return self._data[key]

    def __setitem__(self, key, value):
        """Allows assignment like vels.vec[:] = ... or vels.vec[i] = ..."""
        if not isinstance(value, (np.ndarray, list, tuple, float, int)):
            value = tuple(value)
        self._data[key] = value

    @property
    def x(self) -> np.ndarray:
        return self._data[:, 0]

    @x.setter
    def x(self, value):
        self._data[:, 0] = value

    @property
    def y(self) -> np.ndarray:
        return self._data[:, 1]

    @y.setter
    def y(self, value):
        self._data[:, 1] = value

    @property
    def z(self) -> np.ndarray:
        if self._data.shape[1] < 3:
            raise AttributeError("VectorView has no z component")
        return self._data[:, 2]

    @z.setter
    def z(self, value):
        self._data[:, 2] = value


class BatchView:
    """
    Wraps a NumPy Structured Array and provides .pos.x style access.
    """

    __slots__ = ("_data",)

    def __init__(self, data: np.ndarray):
        self._data = data

    def __getattr__(self, name: str) -> ArrayView:
        try:
            return ArrayView(self._data[name])
        except KeyError:
            raise AttributeError(f"Field '{name}' not found.")

    def __len__(self):
        return len(self._data)
