from game.entities.player import create_ghost
from typing import Optional

from sparrow.net.protocol import Protocol, PacketType
from sparrow.core.components import Transform
from sparrow.core.world import World
from sparrow.net.transport import Address, Transport
from sparrow.types import EntityId


class Client:
    def __init__(self, server_ip: str, server_port: int):
        self.transport = Transport(port=0)  # 0 = Random port
        self.server_addr: Address = (server_ip, server_port)
        self.my_entity_id: Optional[EntityId] = None

        # Send initial handshake
        print(f"[CLIENT] Connecting to {self.server_addr}...")
        self.transport.send(Protocol.pack_connect(), self.server_addr)

    def send_input(self, ax: float, ay: float, buttons: int):
        """
        Send current control state to Host.
        """
        packet = Protocol.pack_input(ax, ay, buttons)
        self.transport.send(packet, self.server_addr)

    def update(self, world: World):
        """Process incoming packets and update the World."""
        packets = self.transport.recv()

        for data, addr in packets:
            if addr != self.server_addr:
                continue

            ptype = Protocol.unpack_packet_type(data)

            if ptype == PacketType.WELCOME:
                eid = Protocol.unpack_welcome(data)
                self.my_entity_id = EntityId(eid)
                print(f"[CLIENT] I am Entity {eid}!")

            elif ptype == PacketType.STATE:
                eid, x, y = Protocol.unpack_entity_state(data)
                self._apply_state(world, EntityId(eid), x, y)
                # print(f"[CLIENT] Received State [EID {eid}, pos: ({x:.2f},{y:.2f})]")

    def _apply_state(self, world: World, eid: EntityId, x: float, y: float):
        """Force the entity to the server's position."""
        # Note: We need to cast int -> EntityId if using strict typing
        # but for now we assume implicit conversion or lenient typing

        if world.has(eid, Transform):
            # Update existing
            trans = world.component(eid, Transform)
            # Simple Snap (Interpolation would go here)
            new_trans = Transform(x=x, y=y, scale=trans.scale, rotation=trans.rotation)
            world.mutate_component(eid, new_trans)
        else:
            # Spawn new "Ghost"
            print(f"[CLIENT] Spawning Ghost {eid}")
            create_ghost(world, eid, x, y)
