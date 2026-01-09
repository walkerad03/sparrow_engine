from typing import Dict, Tuple

from sparrow.net.protocol import Protocol, PacketType
from sparrow.net.transport import Address, Transport


class Host:
    def __init__(self, port: int = 5000):
        self.transport = Transport(port)

        # Map: Address -> Entity ID (The player they control)
        self.clients: Dict[Address, int] = {}

        # Map: Address -> Last known input (ax, ay, buttons)
        self.client_inputs: Dict[Address, Tuple[float, float, int]] = {}

    def update(self):
        packets = self.transport.recv()

        for data, addr in packets:
            try:
                ptype = Protocol.unpack_packet_type(data)
            except ValueError:
                continue

            if ptype == PacketType.CONNECT:
                self._handle_connect(addr)

            elif ptype == PacketType.INPUT:
                if addr in self.clients:
                    ax, ay, buttons = Protocol.unpack_input(data)
                    self.client_inputs[addr] = (ax, ay, buttons)

    def _handle_connect(self, addr: Address):
        if addr not in self.clients:
            print(f"[HOST] New Client Connected: {addr}")

            self.clients[addr] = -1
            self.client_inputs[addr] = (0.0, 0.0, 0)

    def assign_entity(self, addr: Address, eid: int):
        """Called by the Game Scene when it spawns a player for this client."""
        self.clients[addr] = eid
        print(f"[HOST] Assigned Entity {eid} to {addr}")

        # Send Welcome Packet immediately
        packet = Protocol.pack_welcome(eid)
        self.transport.send(packet, addr)

    def broadcast_state(self, eid: int, x: float, y: float):
        """Sends the position of an entity to ALL clients."""
        packet = Protocol.pack_entity_state(eid, x, y)
        for addr in self.clients:
            self.transport.send(packet, addr)
            # print(f"[HOST] Broadcasted state [EID {eid}, pos: ({x:.2f},{y:.2f})]")

    def get_input(self, addr: Address) -> Tuple[float, float, int]:
        return self.client_inputs.get(addr, (0.0, 0.0, 0))
