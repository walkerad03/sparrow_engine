from sparrow.core.components import Transform
from sparrow.core.world import World
from sparrow.net.serializer import PACKET_SNAPSHOT, Serializer
from sparrow.net.transport import Address, Transport
from sparrow.types import EntityId


class Client:
    def __init__(self, server_ip: str, server_port: int):
        self.transport = Transport(port=0)  # 0 = Random port
        self.server_addr: Address = (server_ip, server_port)
        self.connected = False

    def send_input(self, axis_x: float, axis_y: float, actions_mask: int):
        """
        Send current control state to Host.
        """
        packet = Serializer.serialize_input(axis_x, axis_y, actions_mask)
        self.transport.send(packet, self.server_addr)

    def update_world(self, world: World):
        """
        Process incoming snapshots and force-update local entities.
        """
        packets = self.transport.recv()

        for data, addr in packets:
            if addr != self.server_addr:
                continue  # Ignore random packets

            packet_type = data[0]

            if packet_type == PACKET_SNAPSHOT:
                try:
                    eid_raw, new_trans = Serializer.deserialize_snapshot(data)
                    eid = EntityId(eid_raw)

                    # If entity exists, snap it to the new position
                    # (In the future, we would LERP here for smoothness)
                    if world.has(eid, Transform):
                        world.mutate_component(eid, new_trans)
                    else:
                        # Logic to spawn unknown entities would go here
                        # For MVP, we assume entities are pre-spawned or spawned via RPC
                        pass

                except Exception as e:
                    print(f"[NET] Bad Snapshot: {e}")
