from dataclasses import dataclass


@dataclass
class NetworkIdentity:
    net_id: int = -1
    is_local_authority: bool = False  # True if client controls this
