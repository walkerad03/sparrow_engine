from typing import NewType, Tuple

EntityId = NewType("EntityId", int)
ArchetypeMask = NewType("ArchetypeMask", int)

Vector2 = Tuple[float, float]
Vector3 = Tuple[float, float, float]
Rect = Tuple[float, float, float, float]  # x, y, w, h

InputAction = str

Address = Tuple[str, int]
