import socket
from dataclasses import dataclass, field
from typing import Any, Callable, Dict

from sparrow.core.world import World
from sparrow.types import Address, EntityId


@dataclass(frozen=True)
class NetworkHardware:
    socket: socket.socket
    port: int


@dataclass(frozen=True)
class ServerState:
    clients: Dict[Address, int] = field(default_factory=dict)
    connection_map: Dict[int, Address] = field(default_factory=dict)
    next_net_id: int = 1
    next_conn_id: int = 1


@dataclass(frozen=True)
class ClientState:
    server_addr: Address
    connection_id: int = -1
    is_connected: bool = False


@dataclass(frozen=True)
class PrefabRegistry:
    prefabs: Dict[int, Callable[[World, EntityId, Any], None]] = field(
        default_factory=dict
    )
