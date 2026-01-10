from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class NetworkIdentity:
    net_id: int
    owner_id: int = -1


@dataclass
class NetworkInput:
    data: Dict[str, Any] = field(default_factory=dict[str, Any])
