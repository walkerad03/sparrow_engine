import numpy as np

from sparrow.core.components import Transform
from sparrow.ecs.world import World
from sparrow.network.client import EngineNetworkClient
from sparrow.network.components import NetworkIdentity
from sparrow.network.events import NetSpawnEvent, NetTransformEvent


def network_pump_system(world: World) -> None:
    """Pumps the socket to trigger repod callbacks and generate ECS events."""
    client = world.res_get(EngineNetworkClient)
    if client:
        client.pump()


def process_network_events_system(world: World) -> None:
    """Processes incoming network events and updates ECS state for remote entities."""

    # 1. Process Transform Updates
    transform_events = world.event_get(NetTransformEvent)

    if transform_events:
        view = world.query(NetworkIdentity, Transform)

        if len(view) > 0:
            # The ECS array views return numpy arrays.
            # We extract the array of network IDs to find matching entities quickly.
            net_id_array = view.NetworkIdentity.net_id

            for event in transform_events:
                # Find the internal query index corresponding to the incoming net_id
                matching_indices = np.where(net_id_array == event.net_id)[0]

                if len(matching_indices) > 0:
                    idx = matching_indices[0]

                    # Only overwrite the transform if we do not control the entity.
                    # (Local authority entities are governed by local physics/input).
                    if not view.NetworkIdentity.is_local_authority[idx]:
                        view.Transform.pos[idx] = event.pos
                        view.Transform.rot[idx] = event.rot

    # 2. Process Spawns
    spawn_events = world.event_get(NetSpawnEvent)
    for event in spawn_events:
        # Check if the entity already exists to avoid duplicate spawns
        view = world.query(NetworkIdentity)
        existing = False
        if len(view) > 0:
            if event.net_id in view.NetworkIdentity.net_id:
                existing = True

        if not existing:
            # Instantiate a new entity based on the server's spawn event
            new_ent = world.entity_add()
            world.comp_add(
                new_ent,
                NetworkIdentity(net_id=event.net_id, is_local_authority=False),
                Transform(pos=event.pos),
                # Note: You would also attach rendering/physics components here
                # depending on the type of entity spawned.
            )


def network_sync_out_system(world: World) -> None:
    """Reads ECS state and sends updates for entities we have authority over."""
    client = world.res_get(EngineNetworkClient)
    if not client:
        return

    view = world.query(NetworkIdentity, Transform)
    for i in range(len(view)):
        # Only send updates for entities this client controls
        if view.NetworkIdentity.is_local_authority[i]:
            client.send(
                {
                    "action": "transform",
                    "net_id": int(view.NetworkIdentity.net_id[i]),
                    "pos": tuple(view.Transform.pos[i]),
                    "rot": tuple(view.Transform.rot[i]),
                }
            )
