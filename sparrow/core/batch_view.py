import numpy as np


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

    def __getattr__(self, name: str):
        try:
            field = self._data[name]
        except KeyError:
            raise AttributeError(f"Component batch has no field '{name}'")

        # If the field is a 2D array (N, M), wrap it in a VectorView
        if field.ndim == 2 and field.shape[1] in (2, 3, 4):
            return VectorView(field)

        # Otherwise return the raw array (for scalars like 'duration')
        return field

    def __getitem__(self, key):
        """
        Allows direct access to the underlying array rows.
        Essential for iterating IDs: eids[i]
        """
        return self._data[key]

    def __len__(self):
        return len(self._data)
