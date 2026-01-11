import argparse
import ctypes
import sys
from pathlib import Path

import pygame

from game.constants import LOGICAL_RESOLUTION, PHYSICS_FPS, WINDOW_SCALE
from game.entities.player import create_player
from game.scenes.dungeon import DungeonScene
from game.systems.screen_fade import screen_fade_system
from game.systems.smooth_follow import smooth_follow_system
from sparrow.core.world import World
from sparrow.graphics.context import GraphicsContext
from sparrow.graphics.renderer.draw_list import RenderDrawList
from sparrow.graphics.renderer_module import Renderer
from sparrow.input.context import InputContext
from sparrow.input.handler import InputHandler
from sparrow.net import transport
from sparrow.net.components import NetworkIdentity, NetworkInput
from sparrow.net.network import network_system
from sparrow.net.protocol import Protocol
from sparrow.net.resources import (
    ClientState,
    NetworkHardware,
    PrefabRegistry,
    ServerState,
)
from sparrow.systems.hierarchy import hierarchy_system
from sparrow.types import EntityId


def main():
    parser = argparse.ArgumentParser(description="Sparrow Test Game")
    parser.add_argument("--host", action="store_true", help="Start as Server/Host")
    parser.add_argument("--join", type=str, help="Join a server (IP Address)")
    args = parser.parse_args()

    if sys.platform == "win32":
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except AttributeError:
            pass

    ctx = GraphicsContext(LOGICAL_RESOLUTION, WINDOW_SCALE)
    asset_path = Path(__file__).parent / "sparrow" / "graphics" / "shaders"
    renderer = Renderer(ctx, asset_path)

    world = World()

    world.add_resource(RenderDrawList.empty())

    port = 5000 if args.host else 0
    raw_sock = transport.create_socket(port)
    world.add_resource(NetworkHardware(raw_sock, port))

    if args.host:
        print("[GAME] Starting as HOST...")
        pygame.display.set_caption("Sparrow - HOST")
        world.add_resource(ServerState())
    elif args.join:
        print(f"[GAME] Joining {args.join}...")
        pygame.display.set_caption("Sparrow - CLIENT")
        world.add_resource(ClientState(server_addr=(args.join, 5000)))

        print("[NET] Sending Handshake...")
        transport.send_packet(raw_sock, Protocol.pack_connect(), (args.join, 5000))
    else:
        print("[GAME] No args provided, defaulting to HOST.")
        pygame.display.set_caption("Sparrow - SINGLE PLAYER")
        world.add_resource(ServerState())

    registry = PrefabRegistry()

    def spawn_player_wrapper(world: World, eid: EntityId, **kwargs):
        x: int = kwargs.get("x", 100)
        y: int = kwargs.get("y", 100)
        z: int = kwargs.get("z", 100)
        net_id = kwargs.get("net_id", 0)
        owner_id = kwargs.get("owner_id", -1)
        create_player(world, x, y, z, eid=eid)

        world.add_component(eid, NetworkInput())
        world.add_component(eid, NetworkIdentity(net_id, owner_id))

    registry.prefabs[1] = spawn_player_wrapper
    world.add_resource(registry)

    input_handler = InputHandler()
    world.add_resource(input_handler)

    base_ctx = InputContext("default")
    base_ctx.bind(pygame.K_w, "UP")
    base_ctx.bind(pygame.K_s, "DOWN")
    base_ctx.bind(pygame.K_a, "LEFT")
    base_ctx.bind(pygame.K_d, "RIGHT")
    base_ctx.bind(pygame.K_SPACE, "FIRE")

    input_handler.push_context(base_ctx)

    scene = DungeonScene(world, renderer)
    scene.enter()

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(PHYSICS_FPS) / 1000.0

        # Input Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            input_handler.process_event(event)

        network_system(world)

        scene.update(dt)

        screen_fade_system(world, dt, renderer)
        hierarchy_system(world)
        smooth_follow_system(world, dt)

        scene.render()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
