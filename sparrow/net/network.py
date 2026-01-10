from dataclasses import replace
from typing import Any, List, Optional, Tuple

from sparrow.core.components import Transform
from sparrow.core.world import World
from sparrow.net import transport
from sparrow.net.components import NetworkIdentity, NetworkInput
from sparrow.net.protocol import PacketType, Protocol
from sparrow.net.resources import (
    ClientState,
    NetworkHardware,
    PrefabRegistry,
    ServerState,
)
from sparrow.types import Address


def network_system(world: World) -> None:
    hardware = world.try_resource(NetworkHardware)
    if not hardware:
        return

    packets = transport.recv_packets(hardware.socket)

    server_state = world.try_resource(ServerState)
    client_state = world.try_resource(ClientState)

    if server_state is not None:
        new_server = _process_server(world, server_state, hardware, packets)
        if new_server is not server_state:
            world.mutate_resource(new_server)

    if client_state is not None:
        new_client = _process_client(world, client_state, packets)
        if new_client is not client_state:
            world.mutate_resource(new_client)


def _process_server(
    world: World,
    server: ServerState,
    hardware: NetworkHardware,
    packets: List[Tuple[bytes, Address]],
) -> ServerState:
    new_clients: Optional[dict[Address, int]] = None
    new_conn_map: dict[int, Address] = {}
    next_conn_id = server.next_conn_id
    modified = False

    for data, addr in packets:
        ptype = Protocol.unpack_packet_type(data)

        if ptype == PacketType.CONNECT:
            if addr not in server.clients:
                if new_clients is None:
                    new_clients = server.clients.copy()
                    new_conn_map = server.connection_map.copy()

                cid = next_conn_id
                next_conn_id += 1

                new_clients[addr] = cid
                new_conn_map[cid] = addr
                modified = True

                print(f"[NET] Accepted Client {cid} from {addr}")

                transport.send_packet(hardware.socket, Protocol.pack_welcome(cid), addr)

        elif ptype == PacketType.INPUT:
            cid = server.clients.get(addr)
            if cid is not None:
                ax, ay, buttons = Protocol.unpack_input(data)

                for eid, net_id in world.join(NetworkIdentity):
                    assert isinstance(net_id, NetworkIdentity)
                    if net_id.owner_id == cid:
                        input_data: dict[str, Any] = {
                            "ax": ax,
                            "ay": ay,
                            "buttons": buttons,
                        }
                        world.mutate_component(eid, NetworkInput(input_data))
                        break

    if modified:
        return replace(
            server,
            clients=new_clients,
            connection_map=new_conn_map,
            next_conn_id=next_conn_id,
        )

    return server


def _process_client(
    world: World,
    client: ClientState,
    packets: List[Tuple[bytes, Address]],
) -> ClientState:
    modified = False
    new_cid = client.connection_id
    new_connected = client.is_connected

    registry = world.try_resource(PrefabRegistry)

    for data, addr in packets:
        if addr != client.server_addr:
            continue

        ptype = Protocol.unpack_packet_type(data)

        if ptype == PacketType.WELCOME:
            new_cid = Protocol.unpack_welcome(data)
            new_connected = True
            modified = True
            print(f"[NET] Connected to Server! Assigned ID: {new_cid}")

        elif ptype == PacketType.STATE:
            net_eid, x, y = Protocol.unpack_entity_state(data)

            found = False
            for local_eid, net_ident in world.join(NetworkIdentity):
                assert isinstance(net_ident, NetworkIdentity)
                if net_ident.net_id == net_eid:
                    trans = world.component(local_eid, Transform)
                    if trans:
                        world.mutate_component(local_eid, replace(trans, x=x, y=y))
                    found = True
                    break

            if not found and registry:
                if 1 in registry.prefabs:
                    local_eid = world.create_entity()

                    registry.prefabs[1](world, local_eid, x=x, y=y, net_id=net_eid)

    if modified:
        return replace(client, connection_id=new_cid, is_connected=new_connected)

    return client
