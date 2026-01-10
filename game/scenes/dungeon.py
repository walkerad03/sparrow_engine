import math
import random
import time
from dataclasses import replace

from game.constants import GRID_HEIGHT, GRID_WIDTH, TILE_SIZE
from game.spatial.generator import (
    TILE_FLOOR,
    TILE_GOLD,
    TILE_WALL,
    TILE_WATER,
    find_spawn_point,
    generate_dungeon,
)
from sparrow.core.components import BoxCollider, Sprite, Transform
from sparrow.core.world import World
from sparrow.graphics.camera import Camera3D
from sparrow.graphics.light import BlocksLight, PointLight
from sparrow.graphics.renderer import Renderer
from sparrow.input.handler import InputHandler
from sparrow.net import transport
from sparrow.net.components import NetworkIdentity, NetworkInput
from sparrow.net.protocol import Protocol
from sparrow.net.resources import (
    ClientState,
    NetworkHardware,
    PrefabRegistry,
    ServerState,
)
from sparrow.spatial.collision import aabb_vs_aabb, get_world_bounds
from sparrow.spatial.grid import Grid
from sparrow.types import EntityId


class DungeonScene:
    def __init__(
        self,
        world: World,
        renderer: Renderer,
    ):
        self.world = world
        self.renderer = renderer
        self.grid = Grid(GRID_WIDTH, GRID_HEIGHT, TILE_SIZE)

    def enter(self):
        """Called when the scene starts."""
        if self.world.try_resource(ServerState) is not None:
            print("[GAME] Generating Dungeon...")
            self.grid = generate_dungeon(GRID_WIDTH, GRID_HEIGHT, TILE_SIZE)
            self._spawn_map_visuals()

            gx, gy = find_spawn_point(self.grid)
            wx, wy = self.grid.grid_to_world(gx, gy)

            registry = self.world.get_resource(PrefabRegistry)
            if 1 in registry.prefabs:
                registry.prefabs[1](
                    self.world,
                    self.world.create_entity(),
                    x=wx,
                    y=wy,
                    z=0,
                    net_id=0,
                    owner_id=-1,
                )

            print(f"[GAME] Host spawned at Grid({gx}, {gy})")

        cam: Camera3D = self.renderer.camera
        cam.fov_degrees = 30.0
        cam.pitch_angle = -35.0
        cam.distance = 200.0

    def update(self, dt: float):
        """Game Logic."""
        server = self.world.try_resource(ServerState)
        hardware = self.world.try_resource(NetworkHardware)

        if server and hardware:
            registry = self.world.get_resource(PrefabRegistry)

            for cid in server.connection_map:
                has_entity = False
                for _, net_id in self.world.join(NetworkIdentity):
                    if net_id.owner_id == cid:
                        has_entity = True
                        break

                if not has_entity:
                    print(f"[GAME] Spawning Player for Client {cid}")
                    gx, gy = find_spawn_point(self.grid)
                    wx, wy = self.grid.grid_to_world(gx, gy)

                    net_eid = server.next_net_id

                    if 1 in registry.prefabs:
                        new_eid = self.world.create_entity()

                        registry.prefabs[1](
                            self.world,
                            new_eid,
                            x=wx,
                            y=wy,
                            z=0,
                            net_id=net_eid,
                            owner_id=cid,
                        )

            self._process_server_movement(dt)
            self._broadcast_world_state(hardware, server)

        client = self.world.try_resource(ClientState)
        if client and hardware and client.is_connected:
            inp = self.world.get_resource(InputHandler)
            ax = inp.get_axis("LEFT", "RIGHT")
            ay = inp.get_axis("DOWN", "UP")

            packet = Protocol.pack_input(ax, ay, 0)
            transport.send_packet(hardware.socket, packet, client.server_addr)

        my_owner_id = -1
        if client:
            my_owner_id = client.connection_id

        for eid, trans, net in self.world.join(Transform, NetworkIdentity):
            if net.owner_id == my_owner_id:
                self.renderer.camera.update(dt, trans.pos)
                break

        for eid, light in self.world.join(PointLight):
            t = time.time()
            wave_1 = math.sin(t * 10.0 + eid) * 5.0
            wave_2 = math.sin(t * 2.3 + eid) * 15.0

            crackle = 0.0
            if random.random() < 0.05:  # 5% chance per frame
                crackle = random.uniform(-10.0, -30.0)

            base = getattr(light, "base_radius", 150.0)
            new_radius = base + wave_1 + wave_2 + crackle
            if new_radius < 10.0:
                new_radius = 10.0
            self.world.mutate_component(eid, replace(light, radius=new_radius))

    def _process_server_movement(self, dt: float):
        """
        Iterates all entities.
        If Local (Host): Read InputHandler.
        If Remote (Client): Read NetworkInput component.
        """
        inp = self.world.get_resource(InputHandler)

        for eid, trans, collider, net in self.world.join(
            Transform, BoxCollider, NetworkIdentity
        ):
            dx, dy = 0.0, 0.0

            # Case A: It's The Host
            if net.owner_id == -1:
                dx = inp.get_axis("LEFT", "RIGHT")
                dy = inp.get_axis("DOWN", "UP")

            # Case B: It's a Client
            else:
                # Check for NetworkInput component
                net_input = self.world.component(eid, NetworkInput)
                if net_input:
                    dx = net_input.data.get("ax", 0.0)
                    dy = net_input.data.get("ay", 0.0)

            # Apply Physics
            if dx != 0 or dy != 0:
                self._apply_velocity(eid, trans, collider, dx, dy, dt)

    def _apply_velocity(
        self,
        eid: int,
        trans: Transform,
        collider: BoxCollider,
        dx: float,
        dy: float,
        dt: float,
    ):
        speed = 100.0

        # Normalize
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            dx /= length
            dy /= length

        # X Axis
        next_x = trans.x + (dx * speed * dt)
        if not self._check_collision(next_x, trans.y, collider):
            trans = replace(trans, x=next_x)  # Update local var

        # Y Axis
        next_y = trans.y + (dy * speed * dt)
        if not self._check_collision(trans.x, next_y, collider):
            trans = replace(trans, y=next_y)

        self.world.mutate_component(EntityId(eid), trans)

    def _check_collision(self, new_x: float, new_y: float, collider: BoxCollider):
        """Quick collision check against the grid."""
        temp_trans = Transform(x=new_x, y=new_y)
        player_rect = get_world_bounds(temp_trans, collider)
        px, py, pw, ph = player_rect

        start_x, start_y = self.grid.world_to_grid(px, py)
        end_x, end_y = self.grid.world_to_grid(px + pw, py + ph)

        for gx in range(start_x - 1, end_x + 2):
            for gy in range(start_y - 1, end_y + 2):
                if self.grid.get(gx, gy) == TILE_WALL:
                    wx, wy = self.grid.grid_to_world(gx, gy)
                    wall_rect = (
                        wx - TILE_SIZE / 2,
                        wy - TILE_SIZE / 2,
                        TILE_SIZE,
                        TILE_SIZE,
                    )
                    if aabb_vs_aabb(player_rect, wall_rect):
                        return True
        return False

    def _broadcast_world_state(self, hardware: NetworkHardware, server: ServerState):
        """
        Send the position of every network entity to every client.
        """

        for eid, trans, net in self.world.join(Transform, NetworkIdentity):
            packet = Protocol.pack_entity_state(net.net_id, trans.x, trans.y, trans.z)

            for addr in server.clients:
                # Don't send back to owner? (Client Prediction usually handles self)
                # But for now, we sync everything to ensure consistency.
                transport.send_packet(hardware.socket, packet, addr)

    def _spawn_map_visuals(self):
        for x in range(self.grid.width):
            for y in range(self.grid.height):
                tile_id = self.grid.get(x, y)

                wx, wy = self.grid.grid_to_world(x, y)

                if tile_id == TILE_FLOOR:
                    self.world.create_entity(
                        Transform(x=wx, y=wy),
                        Sprite(
                            "floor_1",
                            normal_map_id="floor_1_n",
                            color=(1.0, 1.0, 1.0, 1.0),
                            layer=0,
                        ),  # Grey
                    )

                elif tile_id == TILE_WALL:
                    self.world.create_entity(
                        Transform(x=wx, y=wy),
                        Sprite(
                            "brick",
                            normal_map_id="brick_n",
                            color=(1.0, 1.0, 1.0, 1.0),
                            layer=1,
                        ),  # Grey
                        BoxCollider(width=TILE_SIZE, height=TILE_SIZE),
                        BlocksLight(),
                    )

                elif tile_id == TILE_GOLD:
                    self.world.create_entity(
                        Transform(x=wx, y=wy),
                        Sprite(
                            "wall_mid", color=(1.0, 0.8, 0.0, 1.0), layer=1
                        ),  # Gold Tint
                        BoxCollider(width=TILE_SIZE, height=TILE_SIZE),
                    )

                elif tile_id == TILE_WATER:
                    self.world.create_entity(
                        Transform(x=wx, y=wy),
                        # Water might be transparent or have a different layer
                        Sprite("floor_2", color=(1.0, 1.0, 1.0, 1.0), layer=1),
                        # No Collider? or Trigger Collider?
                    )

    def render(self):
        """Draw the world."""
        self.renderer.render(self.world)
