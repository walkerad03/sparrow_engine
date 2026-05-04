from dataclasses import dataclass

from sparrow.types import Quaternion, Vector3


@dataclass
class NetSpawnEvent:
    net_id: int
    pos: Vector3


@dataclass
class NetTransformEvent:
    net_id: int
    pos: Vector3
    rot: Quaternion
