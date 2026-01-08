import struct
from typing import Tuple

from sparrow.core.components import Transform
from sparrow.types import EntityId

PACKET_SNAPSHOT = 1
PACKET_INPUT = 2
PACKET_WELCOME = 3


class Serializer:
    """
    Handles packing/unpacking components to raw bytes.
    Currently optimized for Transform synchronization.
    """

    _transform_struct = struct.Struct("!ffff")
    _input_struct = struct.Struct("!ffI")
    _welcome_struct = struct.Struct("!BI")

    @classmethod
    def serialize_transform(cls, eid: int, t: Transform) -> bytes:
        """
        Format: [Type=1] [EntityId] [x, y, rot, scale]
        """
        header = struct.pack("!BI", PACKET_SNAPSHOT, eid)
        payload = cls._transform_struct.pack(t.x, t.y, t.rotation, t.scale)
        return header + payload

    @classmethod
    def deserialize_snapshot(cls, data: bytes) -> Tuple[int, Transform]:
        """
        Returns (EntityId, Transform)
        """
        # Header is 5 bytes (1B Type + 4B ID)
        eid: EntityId = struct.unpack("!BI", data[:5])[1]

        # Payload is 16 bytes
        x, y, rot, scale = cls._transform_struct.unpack(data[5:21])
        return eid, Transform(x, y, rotation=rot, scale=scale)

    @classmethod
    def serialize_input(cls, axis_x: float, axis_y: float, actions: int) -> bytes:
        """
        Format: [Type=2] [x, y, mask]
        """
        header = struct.pack("!B", PACKET_INPUT)
        payload = cls._input_struct.pack(axis_x, axis_y, actions)
        return header + payload

    @classmethod
    def deserialize_input(cls, data: bytes) -> Tuple[float, float, int]:
        # Skip 1 byte header
        return cls._input_struct.unpack(data[1:13])

    @classmethod
    def serialize_welcome(cls, eid: int) -> bytes:
        return cls._welcome_struct.pack(PACKET_WELCOME, eid)

    @classmethod
    def deserialize_welcome(cls, data: bytes) -> int:
        # Returns the EntityId assigned to this client
        return cls._welcome_struct.unpack(data)[1]
