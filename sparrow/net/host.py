from typing import Dict, Set, Tuple

from sparrow.core.components import Transform
from sparrow.core.world import World
from sparrow.net.serializer import PACKET_INPUT, Serializer
from sparrow.net.transport import Address, Transport


class Host:
    def __init__(self, port: int = 5000):
        self.transport = Transport(port)
        self.clients: Set[Address] = set()

        # Map: Address -> Last known input state
        # (We store inputs to apply them every frame until new ones arrive)
        self.client_inputs: Dict[Address, Tuple[float, float, int]] = {}

    def send_welcome(self, addr: Address, eid: int):
        """Tells a specific client which Entity ID they control."""
        packet = Serializer.serialize_welcome(eid)
        self.transport.send(packet, addr)

    def process_network(self):
        """
        1. Receive packets.
        2. Identify new clients.
        3. Store their inputs.
        """
        packets = self.transport.recv()
        for data, addr in packets:
            if addr not in self.clients:
                print(f"[NET] New Client: {addr}")
                self.clients.add(addr)

            # Use the first byte to identify packet type
            packet_type = data[0]

            if packet_type == PACKET_INPUT:
                try:
                    # Unpack (ax, ay, mask)
                    inp = Serializer.deserialize_input(data)
                    self.client_inputs[addr] = inp
                except Exception as e:
                    print(f"[NET] Bad Input Packet: {e}")

    def broadcast_state(self, world: World):
        """
        Serialize all Transforms and send to all clients.
        """
        # In a real engine, we would bundle these into one large packet.
        # For simplicity, we send one UDP packet per entity (Inefficient but easy).
        for eid, transform in world.join(Transform):
            packet = Serializer.serialize_transform(int(eid), transform)

            for client in self.clients:
                self.transport.send(packet, client)

    def get_input_for(self, addr: Address) -> Tuple[float, float, int]:
        return self.client_inputs.get(addr, (0.0, 0.0, 0))
