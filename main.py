import ctypes
import sys
import argparse
from pathlib import Path

import pygame

from game.constants import LOGICAL_RESOLUTION, PHYSICS_FPS, WINDOW_SCALE
from game.scenes.dungeon import DungeonScene
from sparrow.core.world import World
from sparrow.graphics.context import GraphicsContext
from sparrow.graphics.renderer import Renderer
from sparrow.input.context import InputContext
from sparrow.input.handler import InputHandler
from sparrow.net.client import Client
from sparrow.net.host import Host


def main():
    parser = argparse.ArgumentParser(description="Sparrow Test Game")
    parser.add_argument("--host", action="store_true", help="Start as Server/Host")
    parser.add_argument("--join", type=str, help="Join a server (IP Address)")
    args = parser.parse_args()

    ctx = GraphicsContext(LOGICAL_RESOLUTION, WINDOW_SCALE)
    asset_path = Path(__file__).parent / "assets" / "shaders"
    renderer = Renderer(ctx, asset_path)

    if sys.platform == "win32":
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except AttributeError:
            pass

    world = World()

    host = None
    client = None

    if args.host:
        print("[GAME] Starting as HOST...")
        pygame.display.set_caption("Sparrow - HOST")
        host = Host(port=5000)
    elif args.join:
        print(f"[GAME] Joining {args.join}...")
        pygame.display.set_caption("Sparrow - CLIENT")
        client = Client(server_ip=args.join, server_port=5000)
    else:
        print("[GAME] No args provided, defaulting to HOST.")
        pygame.display.set_caption("Sparrow - SINGLE PLAYER")
        host = Host(port=5000)

    input_handler = InputHandler()
    world.add_resource(input_handler)

    base_ctx = InputContext("default")
    base_ctx.bind(pygame.K_w, "UP")
    base_ctx.bind(pygame.K_s, "DOWN")
    base_ctx.bind(pygame.K_a, "LEFT")
    base_ctx.bind(pygame.K_d, "RIGHT")
    base_ctx.bind(pygame.K_SPACE, "FIRE")

    input_handler.push_context(base_ctx)

    scene = DungeonScene(world, renderer, host, client)
    scene.enter()

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(PHYSICS_FPS) / 1000.0

        # Input Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            input_handler.process_event(event)

        # Networking
        if host:
            host.process_network()
            scene.update(dt)
            host.broadcast_state(world)

        elif client:
            ax = input_handler.get_axis("LEFT", "RIGHT")
            ay = input_handler.get_axis("DOWN", "UP")
            client.send_input(ax, ay, 0)

            client.update_world(world)

            scene.update(dt)

        scene.render()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
