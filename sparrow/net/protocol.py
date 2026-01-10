import struct
from enum import IntEnum, auto
from typing import Optional, Tuple

from sparrow.types import EntityId


class PacketType(IntEnum):
    CONNECT = auto()  # Client -> Host: Request spawn
    WELCOME = auto()  # Host -> Client: Assign Entity ID
    INPUT = auto()  # Client -> Host: Input button data
    STATE = auto()  # Host -> Client: Current world state


class Protocol:
    VERSION = 1

    # --- Internal Structs ---
    # ! = Network Endian (Big Endian)
    # B = Unsigned Char (1 byte), I = Unsigned Int (4 bytes), f = Float
    _HEADER = struct.Struct("!BB")  # [Type, Version]
    _WELCOME = struct.Struct("!BI")  # [Type, EntityID]
    _INPUT = struct.Struct("!BffB")  # [Type, X, Y, Buttons]
    _STATE = struct.Struct("!BIfff")  # [Type, EntityID, X, Y]

    @staticmethod
    def unpack_packet_type(data: bytes) -> Optional[PacketType]:
        if len(data) < 1:
            raise ValueError("Empty packet")
        try:
            return PacketType(data[0])
        except ValueError:
            return PacketType(0) if 0 in PacketType._value2member_map_ else None

    @classmethod
    def pack_connect(cls) -> bytes:
        return cls._HEADER.pack(PacketType.CONNECT, cls.VERSION)

    @classmethod
    def pack_welcome(cls, eid: int) -> bytes:
        return cls._WELCOME.pack(PacketType.WELCOME, eid)

    @classmethod
    def pack_input(cls, ax: float, ay: float, buttons: int) -> bytes:
        return cls._INPUT.pack(PacketType.INPUT, ax, ay, buttons)

    @classmethod
    def pack_entity_state(cls, eid: int, x: float, y: float, z: float) -> bytes:
        return cls._STATE.pack(PacketType.STATE, eid, x, y, z)

    @classmethod
    def unpack_welcome(cls, data: bytes) -> int:
        return cls._WELCOME.unpack(data)[1]

    @classmethod
    def unpack_input(cls, data: bytes) -> Tuple[float, float, int]:
        # Returns (ax, ay, buttons)
        _, ax, ay, btns = cls._INPUT.unpack(data)
        return ax, ay, btns

    @classmethod
    def unpack_entity_state(cls, data: bytes) -> Tuple[int, float, float, float]:
        # Returns (eid, x, y)
        _, eid, x, y, z = cls._STATE.unpack(data)
        return eid, x, y, z
