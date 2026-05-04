import logging

from repod import ConnectionListener

from sparrow.ecs.world import World
from sparrow.network.events import NetSpawnEvent, NetTransformEvent

logger = logging.getLogger("sparrow.network")


class EngineNetworkClient(ConnectionListener):
    def __init__(self, world: World):
        super().__init__()
        self.world = world

    def connect_to(self, host: str, port: int):
        self.connect(host, port)
        logger.info(f"Connecting to {host}:{port}")

    def Network_connected(self, data: dict) -> None:
        logger.info("Connected to server.")

    def Network_error(self, data: dict) -> None:
        logger.error(f"Network error: {data['error']}")

    def Network_spawn(self, data: dict) -> None:
        self.world.event_add(
            NetSpawnEvent(net_id=data["net_id"], pos=data["pos"])
        )

    def Network_transform(self, data: dict) -> None:
        self.world.event_add(
            NetTransformEvent(
                net_id=data["net_id"], pos=data["pos"], rot=data["rot"]
            )
        )
